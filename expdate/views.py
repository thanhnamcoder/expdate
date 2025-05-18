from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from .api import is_group_manager
from datetime import datetime
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .models import Item
from django.contrib.auth import logout
from django.views.decorators.http import require_POST
import json
import calendar

@login_required
@csrf_exempt
def delete_item_view(request, item_id):
    try:
        item = Item.objects.get(id=item_id)
    except Item.DoesNotExist:
        return HttpResponse('Item not found', status=404)
    # Kiểm tra quyền xóa bằng is_group_manager
    if not is_group_manager(request.user, item.user):
        return HttpResponse('Forbidden', status=403)
    if request.method == 'POST':
        try:
            item = Item.objects.get(id=item_id)
            item.delete()
            # AJAX request: return 204 No Content or JSON
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return HttpResponse(status=204)
            else:
                return redirect('home')
        except Item.DoesNotExist:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'error': 'Item not found'}, status=404)
            return HttpResponse('Item not found', status=404)
    return HttpResponse('Method not allowed', status=405)

@login_required
@csrf_exempt
def edit_item_view(request, item_id):
    try:
        item = Item.objects.get(id=item_id)
    except Item.DoesNotExist:
        return HttpResponse('Item not found', status=404)
    # Kiểm tra quyền sửa bằng is_group_manager 
    if not is_group_manager(request.user, item.user):
        return HttpResponse('Forbidden', status=403)
    try:
        item = Item.objects.get(id=item_id)
    except Item.DoesNotExist:
        return HttpResponse('Item not found', status=404)
    if request.method == 'POST':
        itembarcode = request.POST.get('itembarcode')
        itemname = request.POST.get('itemname')
        quantity = request.POST.get('quantity')
        expdate = request.POST.get('expdate')
        if itembarcode and itemname and quantity and expdate:
            try:
                expdate_obj = datetime.strptime(expdate, "%Y-%m-%d").date()
                item.itembarcode = itembarcode
                item.itemname = itemname
                item.quantity = quantity
                item.expdate = expdate_obj
                item.save()
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return HttpResponse(status=204)
                else:
                    return redirect('home')
            except Exception:
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'error': 'Dữ liệu không hợp lệ.'}, status=400)
                return HttpResponse('Dữ liệu không hợp lệ.', status=400)
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'error': 'Vui lòng nhập đầy đủ thông tin.'}, status=400)
            return HttpResponse('Vui lòng nhập đầy đủ thông tin.', status=400)
    # GET: Hiển thị form sửa
    return render(request, 'edit_item.html', {'item': item})

def guest_view(request):
    return render(request, 'guest.html')

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    error_message = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            error_message = 'Tên đăng nhập hoặc mật khẩu không đúng.'
    return render(request, 'login.html', {'error_message': error_message})

def register_view(request):
    if request.method == 'POST':
        if request.content_type == 'application/json':
            data = json.loads(request.body.decode())
            username = data.get('username', '').strip()
            password = data.get('password', '').strip()
            name = data.get('name', '').strip()
            group_label = data.get('group', '').strip().lower()
            email = data.get('email', '').strip()
        else:
            username = request.POST.get('username', '').strip()
            password = request.POST.get('password', '').strip()
            name = request.POST.get('name', '').strip()
            group_label = request.POST.get('group', '').strip().lower()
            email = request.POST.get('email', '').strip()
        if not username:
            return JsonResponse({'error': 'Tên đăng nhập không được để trống.'}, status=400)
        if not password:
            return JsonResponse({'error': 'Mật khẩu không được để trống.'}, status=400)
        if not name:
            return JsonResponse({'error': 'Họ và tên không được để trống.'}, status=400)
        if User.objects.filter(username=username).exists():
            return JsonResponse({'error': 'Tên đăng nhập đã tồn tại.'}, status=400)
        user = User.objects.create_user(username=username, password=password, first_name=name, email=email)
        if group_label:
            group, created = Group.objects.get_or_create(name=group_label)
            user.groups.clear()
            user.groups.add(group)
        user.save()
        return JsonResponse({'success': True})
    return render(request, 'register.html')

@login_required
def home_view(request):
    message = None
    if request.method == 'POST':
        itembarcode = request.POST.get('itembarcode')
        itemname = request.POST.get('itemname')
        quantity = request.POST.get('quantity')
        mfgdate = request.POST.get('mfgdate')
        months = request.POST.get('months')
        expdate = request.POST.get('expdate')
        if itembarcode and itemname and quantity and (expdate or (mfgdate and months)):
            try:
                if expdate:
                    expdate_obj = datetime.strptime(expdate, "%Y-%m-%d").date()
                else:
                    mfgdate_obj = datetime.strptime(mfgdate, "%Y-%m-%d").date()
                    months_int = int(months)
                    year = mfgdate_obj.year + (mfgdate_obj.month + months_int - 1) // 12
                    month = (mfgdate_obj.month + months_int - 1) % 12 + 1
                    day = mfgdate_obj.day
                    last_day = calendar.monthrange(year, month)[1]
                    if day > last_day:
                        day = last_day
                    expdate_obj = datetime.date(year, month, day)
                Item.objects.create(
                    user=request.user,
                    itembarcode=itembarcode,
                    itemname=itemname,
                    quantity=quantity,
                    expdate=expdate_obj
                )
                message = 'Lưu thành công!'
            except Exception as e:
                message = 'Dữ liệu không hợp lệ.'
        else:
            message = 'Vui lòng nhập đầy đủ thông tin.'

    # Nếu là superuser thì xem tất cả
    if request.user.is_superuser:
        items = Item.objects.all().order_by('-created_at')
    else:
        user_groups = request.user.groups.all()
        if user_groups:
            group = user_groups[0]
            group_users = group.user_set.all()
            items = Item.objects.filter(user__in=group_users).order_by('-created_at')
        else:
            items = Item.objects.filter(user=request.user).order_by('-created_at')

    today = datetime.today()
    days = list(range(1, 32))
    months = list(range(1, 13))
    years = list(range(today.year, today.year + 11))

    return render(request, 'home.html', {
        'items': items,
        'message': message,
        'show_group': request.user.is_superuser,
        'days': days,
        'months': months,
        'years': years,
        'default_day': today.day,
        'default_month': today.month,
        'default_year': today.year
    })

def logout_view(request):
    logout(request)
    return redirect('login')


def printmode_view(request):
    return render(request, 'printmode.html')

@csrf_exempt
@require_POST
def api_login(request):
    import json
    try:
        data = json.loads(request.body.decode())
        username = data.get('username')
        password = data.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'error': 'Tên đăng nhập hoặc mật khẩu không đúng.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)