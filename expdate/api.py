from django.http import JsonResponse, HttpResponseNotAllowed, HttpResponseForbidden, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from expdate.models import Item
from django.contrib.auth.models import User
import json
from datetime import datetime, timedelta
import mysql.connector
import re
def is_group_manager(user, item_user):
    """
    Trả về True nếu:
    - user là superuser
    - user là group manager (is_sm) và cùng nhóm với item_user
    - user chính là chủ sở hữu dữ liệu (item_user)
    """
    if user.is_superuser:
        return True
    if hasattr(user, 'userprofile') and getattr(user.userprofile, 'is_sm', False):
        user_groups = set(user.groups.values_list('id', flat=True))
        item_user_groups = set(item_user.groups.values_list('id', flat=True))
        if user_groups & item_user_groups:
            return True
    return item_user == user

@method_decorator(csrf_exempt, name='dispatch')
class ItemListAPI(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        # Nếu là superuser thì xem tất cả
        if request.user.is_superuser:
            items = Item.objects.all()
        else:
            user_groups = request.user.groups.all()
            if user_groups:
                group = user_groups[0]
                group_users = group.user_set.all()
                items = Item.objects.filter(user__in=group_users)
            else:
                items = Item.objects.filter(user=request.user)

        data = [
            {
                'id': item.id,
                'itembarcode': item.itembarcode,
                'itemname': item.itemname,
                'quantity': item.quantity,
                'expdate': item.expdate.strftime('%Y-%m-%d'),
                'user_id': item.user.id,
                'username': item.user.first_name or item.user.username,
                'user_group_id': item.user.groups.first().id if item.user.groups.exists() else None,
                'can_delete': is_group_manager(request.user, item.user),
                'can_edit': is_group_manager(request.user, item.user)
            } for item in items
        ]

        return JsonResponse({'items': data})

    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        try:
            body = json.loads(request.body.decode())
            itembarcode = body.get('itembarcode')
            itemname = body.get('itemname')
            quantity = body.get('quantity')
            expdate = body.get('expdate')
            if not (itembarcode and itemname and quantity and expdate):
                return JsonResponse({'error': 'Missing fields'}, status=400)
            expdate_obj = datetime.strptime(expdate, '%d/%m/%Y').date()
            # Kiểm tra barcode đã tồn tại với user này chưa
            existing_items = Item.objects.filter(user=request.user, itembarcode=itembarcode)
            for item in existing_items:
                if item.expdate == expdate_obj:
                    # Nếu expdate trùng, cộng quantity và update
                    try:
                        item.quantity += int(quantity)
                    except Exception:
                        item.quantity = int(item.quantity) + int(quantity)
                    item.itemname = itemname  # Có thể cập nhật tên mới nhất
                    item.save()
                    return JsonResponse({'id': item.id, 'updated': True}, status=200)
            # Nếu không có hoặc expdate khác, tạo mới
            item = Item.objects.create(
                user=request.user,
                itembarcode=itembarcode,
                itemname=itemname,
                quantity=quantity,
                expdate=expdate_obj
            )
            return JsonResponse({'id': item.id, 'created': True}, status=201)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    def delete(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        try:
            body = json.loads(request.body.decode()) if request.body else {}
            item_ids = body.get('item_ids')
            if not item_ids or not isinstance(item_ids, list):
                return JsonResponse({'error': 'Missing or invalid item_ids'}, status=400)
            deleted = []
            forbidden = []
            notfound = []
            for item_id in item_ids:
                try:
                    item = Item.objects.get(id=item_id)
                    if not is_group_manager(request.user, item.user):
                        forbidden.append(item_id)
                        continue
                    item.delete()
                    deleted.append(item_id)
                except Item.DoesNotExist:
                    notfound.append(item_id)
            return JsonResponse({'deleted': deleted, 'forbidden': forbidden, 'notfound': notfound, 'success': True})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

@method_decorator(csrf_exempt, name='dispatch')
class ItemDetailAPI(View):
    def get(self, request, item_id):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        try:
            item = Item.objects.get(id=item_id)
            # Chỉ group manager cùng nhóm hoặc chính chủ sở hữu mới xem được
            if not is_group_manager(request.user, item.user):
                return HttpResponseForbidden()
            data = {
                'id': item.id,
                'itembarcode': item.itembarcode,
                'itemname': item.itemname,
                'quantity': item.quantity,
                'expdate': item.expdate.strftime('%Y-%m-%d'),
                'user_id': item.user.id,
                'username': item.user.first_name or item.user.username,
                'user_group_id': item.user.groups.first().id if item.user.groups.exists() else None,
                'can_delete': is_group_manager(request.user, item.user),
                'can_edit': is_group_manager(request.user, item.user)
            }
            return JsonResponse(data)
        except Item.DoesNotExist:
            return HttpResponseNotFound()

    def put(self, request, item_id):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        try:
            item = Item.objects.get(id=item_id)
            # Chỉ group manager cùng nhóm hoặc chính chủ sở hữu mới sửa được
            if not is_group_manager(request.user, item.user):
                return HttpResponseForbidden()
            body = json.loads(request.body.decode())
            item.itembarcode = body.get('itembarcode', item.itembarcode)
            item.itemname = body.get('itemname', item.itemname)
            item.quantity = body.get('quantity', item.quantity)
            expdate = body.get('expdate')
            if expdate:
                item.expdate = datetime.strptime(expdate, '%Y-%m-%d').date()
            item.save()
            return JsonResponse({'success': True})
        except Item.DoesNotExist:
            return HttpResponseNotFound()
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    def delete(self, request, item_id):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        try:
            item = Item.objects.get(id=item_id)
            # Chỉ group manager cùng nhóm hoặc chính chủ sở hữu mới xóa được
            if not is_group_manager(request.user, item.user):
                return HttpResponseForbidden()
            item.delete()
            return JsonResponse({'success': True})
        except Item.DoesNotExist:
            return HttpResponseNotFound()

@method_decorator(csrf_exempt, name='dispatch')
class ExpiringSoonAPI(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        # Nếu là superuser thì xem tất cả
        if request.user.is_superuser:
            items = Item.objects.all()
        else:
            user_groups = request.user.groups.all()
            if user_groups:
                group = user_groups[0]
                group_users = group.user_set.all()
                items = Item.objects.filter(user__in=group_users)
            else:
                items = Item.objects.filter(user=request.user)

        current_date = datetime.now().date()
        upper_threshold = current_date + timedelta(days=7)

        # Sản phẩm sắp hết hạn: expdate > current_date và expdate <= current_date + 7
        expiring_soon_items = items.filter(expdate__gt=current_date, expdate__lte=upper_threshold)
        # Sản phẩm đã hết hạn: expdate < current_date
        expired_items = items.filter(expdate__lt=current_date)

        expiring_soon_data = [
            {
                'id': item.id,
                'itembarcode': item.itembarcode,
                'itemname': item.itemname,
                'quantity': item.quantity,
                'expdate': item.expdate.strftime('%Y-%m-%d'),
                'user_id': item.user.id,
                'username': item.user.first_name or item.user.username,
                'user_group_id': item.user.groups.first().id if item.user.groups.exists() else None
            } for item in expiring_soon_items
        ]
        expired_data = [
            {
                'id': item.id,
                'itembarcode': item.itembarcode,
                'itemname': item.itemname,
                'quantity': item.quantity,
                'expdate': item.expdate.strftime('%Y-%m-%d'),
                'user_id': item.user.id,
                'username': item.user.first_name or item.user.username,
                'user_group_id': item.user.groups.first().id if item.user.groups.exists() else None
            } for item in expired_items
        ]

        return JsonResponse({'expiring_soon': expiring_soon_data, 'expired': expired_data})

@csrf_exempt
def get_item(request):
    query = request.GET.get('barcode', '').strip()

    if not query:
        return JsonResponse({'success': False, 'error': 'Không có dữ liệu được cung cấp'})

    try:
        conn = mysql.connector.connect(
            host="103.97.126.29",
            user="vvesnzbk_product_data",
            password="Nguyen2004nam@",
            database="vvesnzbk_product_data"
        )
        cursor = conn.cursor(dictionary=True)

        # Nếu query có 6 số chính xác → item_code
        if re.fullmatch(r'\d{6}', query):
            sql = """
                SELECT item_barcode, item_code, item_name, department, category, sub_category, vendor_code, vendor_name
                FROM product_data
                WHERE item_code = %s
            """
            cursor.execute(sql, (query,))
            result = cursor.fetchone()
            if result:
                cursor.close()
                conn.close()
                return JsonResponse({'success': True, 'data': result})

        # Tìm chính xác barcode
        sql = """
            SELECT item_barcode, item_code, item_name, department, category, sub_category, vendor_code, vendor_name
            FROM product_data
            WHERE item_barcode = %s
        """
        cursor.execute(sql, (query,))
        result = cursor.fetchone()
        if result:
            cursor.close()
            conn.close()
            return JsonResponse({'success': True, 'data': result})

        # Tìm 6 số đầu hoặc 6 số cuối (giúp tìm với barcode dài hơn)
        if len(query) > 6:
            start6 = query[:6]
            end6 = query[-6:]
            sql = """
                SELECT item_barcode, item_code, item_name, department, category, sub_category, vendor_code, vendor_name
                FROM product_data
                WHERE item_barcode LIKE %s OR item_barcode LIKE %s
            """
            cursor.execute(sql, (f'{start6}%', f'%{end6}'))
            result = cursor.fetchone()
            if result:
                cursor.close()
                conn.close()
                return JsonResponse({'success': True, 'data': result})

        # Tìm barcode chứa query ở bất kỳ vị trí nào (cẩn thận về performance)
        sql = """
            SELECT item_barcode, item_code, item_name, department, category, sub_category, vendor_code, vendor_name
            FROM product_data
            WHERE item_barcode LIKE %s
            LIMIT 1
        """
        cursor.execute(sql, (f'%{query}%',))
        result = cursor.fetchone()
        if result:
            cursor.close()
            conn.close()
            return JsonResponse({'success': True, 'data': result})

        cursor.close()
        conn.close()
        return JsonResponse({'success': False, 'error': 'Không tìm thấy sản phẩm'})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
def product_data_api(request):
    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])
    try:
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 50))
        search = request.GET.get('search', '').strip()
        offset = (page - 1) * page_size
        conn = mysql.connector.connect(
            host="103.97.126.29",
            user="vvesnzbk_product_data",
            password="Nguyen2004nam@",
            database="vvesnzbk_product_data"
        )
        cursor = conn.cursor(dictionary=True)
        base_query = "SELECT item_barcode, item_code, item_name, department, category, sub_category, vendor_code, vendor_name FROM product_data"
        count_query = "SELECT COUNT(*) as total FROM product_data"
        params = []
        if search:
            where = " WHERE item_barcode LIKE %s OR item_code LIKE %s OR item_name LIKE %s OR department LIKE %s OR category LIKE %s OR sub_category LIKE %s OR vendor_code LIKE %s OR vendor_name LIKE %s"
            base_query += where
            count_query += where
            search_val = f"%{search}%"
            params = [search_val]*8
        base_query += " ORDER BY item_barcode LIMIT %s OFFSET %s"
        params += [page_size, offset]
        cursor.execute(count_query, params[:len(params)-2] if search else [])
        total = cursor.fetchone()['total']
        cursor.execute(base_query, params)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        total_pages = (total + page_size - 1) // page_size
        return JsonResponse({'success': True, 'data': rows, 'total': total, 'total_pages': total_pages, 'page': page, 'page_size': page_size})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@method_decorator(csrf_exempt, name='dispatch')
class GroupItemsAPI(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Unauthorized'}, status=401)

        try:
            # Fetch items for the user's group or all user data if no group
            user_groups = request.user.groups.all()
            if user_groups:
                group = user_groups[0]
                group_users = group.user_set.all()
                items = Item.objects.filter(user__in=group_users)
            else:
                items = Item.objects.filter(user=request.user)

            data = [
                {
                    'id': item.id,
                    'itembarcode': item.itembarcode,
                    'itemname': item.itemname,
                    'quantity': item.quantity,
                    'expdate': item.expdate.strftime('%Y-%m-%d'),
                    'user_id': item.user.id,
                    'username': item.user.first_name or item.user.username,
                    'can_edit': is_group_manager(request.user, item.user),
                    'can_delete': is_group_manager(request.user, item.user),
                } for item in items
            ]

            return JsonResponse({'items': data})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

# In urls.py, add:
# from expdate.api import ItemListAPI, ItemDetailAPI, ExpiringSoonAPI
# urlpatterns += [
#     path('api/items/', ItemListAPI.as_view(), name='api_items'),
#     path('api/items/<int:item_id>/', ItemDetailAPI.as_view(), name='api_item_detail'),
#     path('api/items/expiring_soon/', ExpiringSoonAPI.as_view(), name='api_expiring_soon'),
# ]
