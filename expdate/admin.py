from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django import forms
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from .models import Item, UserProfile
from .forms import ItemImportForm
import pandas as pd
import mysql.connector

# Inline group assignment for User
class GroupInline(admin.TabularInline):
    model = User.groups.through
    extra = 1

class GroupSelectionForm(forms.Form):
    group = forms.ModelChoiceField(queryset=Group.objects.all(), label="Chọn nhóm")

def add_users_to_group_view(request, queryset):
    if request.method == 'POST':
        form = GroupSelectionForm(request.POST)
        if form.is_valid():
            group = form.cleaned_data['group']
            for user in queryset:
                user.groups.add(group)
            messages.success(request, f"Đã thêm {queryset.count()} user vào nhóm '{group.name}'")
            return redirect('..')
    else:
        form = GroupSelectionForm()

    return render(request, 'admin/add_users_to_group.html', {
        'form': form,
        'users': queryset,
    })

# Hiển thị nhóm của user trong admin
class SingleGroupInlineForm(forms.ModelForm):
    group = forms.ModelChoiceField(queryset=Group.objects.all(), required=False, label='Nhóm')

    class Meta:
        model = UserProfile
        fields = ('is_sm',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and hasattr(self.instance, "user") and self.instance.user:
            user_groups = self.instance.user.groups.all()
            self.fields['group'].initial = user_groups[0].id if user_groups else None

    def save(self, commit=True):
        userprofile = super().save(commit=False)
        group = self.cleaned_data.get('group')
        user = userprofile.user
        if group:
            # Xóa hết group cũ, chỉ giữ group mới
            user.groups.clear()
            user.groups.add(group)
        else:
            # Nếu group là None, xóa tất cả các nhóm
            user.groups.clear()
        if commit:
            userprofile.save()
        return userprofile

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Thông tin bổ sung'
    fk_name = 'user'
    form = SingleGroupInlineForm
    fields = ('is_sm', 'group')

class CustomUserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = BaseUserAdmin.list_display + ('get_groups', 'is_superuser', 'is_sm')
    list_filter = BaseUserAdmin.list_filter + ('is_superuser',)
    actions = ['add_to_group_action']

    def get_groups(self, obj):
        return ", ".join([g.name for g in obj.groups.all()])
    get_groups.short_description = 'Nhóm'

    def is_sm(self, obj):
        return hasattr(obj, 'userprofile') and obj.userprofile.is_sm
    is_sm.boolean = True
    is_sm.short_description = 'Quản lý nhóm (is_sm)'

    # Đổi tên cột staff thành Admin
    def admin(self, obj):
        return obj.is_staff
    admin.boolean = True
    admin.short_description = 'Admin'

    # Ẩn cột staff, thêm cột admin
    def get_list_display(self, request):
        display = list(super().get_list_display(request))
        if 'is_staff' in display:
            display.remove('is_staff')
        if 'admin' not in display:
            display.append('admin')
        return display

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        # Loại bỏ phần User permissions
        fieldsets = [fs for fs in fieldsets if fs[0] != 'Permissions']
        return fieldsets

    def add_to_group_action(self, request, queryset):
        if 'apply' in request.POST:
            form = GroupSelectionForm(request.POST)
            if form.is_valid():
                group = form.cleaned_data['group']
                for user in queryset:
                    # Clear existing groups and add the new group
                    user.groups.clear()
                    user.groups.add(group)
                self.message_user(request, f"Đã thêm {queryset.count()} người dùng vào nhóm '{group.name}'", messages.SUCCESS)
                return redirect(request.get_full_path())
        else:
            form = GroupSelectionForm()
        return TemplateResponse(request, 'admin/add_users_to_group.html', context={
            'users': queryset,
            'form': form,
            'title': 'Thêm người dùng vào nhóm',
            'opts': self.model._meta,
            'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
        })
    add_to_group_action.short_description = "Add selected users to group"

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# Custom admin for Item
@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("itembarcode", "itemname", "quantity", "expdate", "user")
    search_fields = ("itembarcode", "itemname")
    actions = ["delete_selected"]
    change_list_template = "admin/item_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-excel/', self.admin_site.admin_view(self.import_excel), name='item-import-excel'),
        ]
        return custom_urls + urls

    def import_excel(self, request):
        if request.method == 'POST':
            form = ItemImportForm(request.POST, request.FILES)
            if form.is_valid():
                file = form.cleaned_data['file']
                try:
                    # Đọc file Excel ban đầu để tìm hàng chứa tiêu đề cột
                    df = pd.read_excel(file, header=None)  # Đọc toàn bộ file không có tiêu đề

                    # Tự động dò tìm hàng chứa tiêu đề cột
                    expected_columns = ['Item Barcode', 'Item Code', 'Item Name', 'Department', 'Category',
                                        'Sub Category', 'Vendor Code', 'Vendor Name']
                    header_row = None

                    for i in range(len(df)):
                        row = df.iloc[i]
                        if all(col in row.values for col in expected_columns):
                            header_row = i
                            break

                    if header_row is None:
                        raise ValueError("Không tìm thấy hàng chứa tiêu đề cột phù hợp.")

                    # Đọc lại file Excel từ hàng tiêu đề cột
                    df = pd.read_excel(file, header=header_row, dtype={'Item Barcode': str, 'Item Code': str})
                    df.columns = df.columns.str.strip()

                    # Chuyển đổi file Excel thành CSV trước khi xử lý
                    import os
                    import tempfile

                    with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_csv:
                        temp_csv_path = temp_csv.name

                    df.to_csv(temp_csv_path, index=False, encoding='utf-8')

                    # Đọc lại file CSV để xử lý
                    df = pd.read_csv(temp_csv_path, dtype={'Item Barcode': str, 'Item Code': str})

                    # Xóa file CSV tạm sau khi xử lý
                    os.remove(temp_csv_path)

                    columns = {
                        'Item Barcode': 'item_barcode',
                        'Item Code': 'item_code',
                        'Item Name': 'item_name',
                        'Department': 'department',
                        'Category': 'category',
                        'Sub Category': 'sub_category',
                        'Vendor Code': 'vendor_code',
                        'Vendor Name': 'vendor_name'
                    }
                    df_filtered = df[list(columns.keys())].rename(columns=columns)

                    # Kiểm tra dữ liệu hợp lệ
                    invalid_barcode = df_filtered[df_filtered['item_barcode'].str.contains(r'[^0-9]', na=False)]
                    invalid_code = df_filtered[df_filtered['item_code'].str.contains(r'[^0-9]', na=False)]
                    empty_rows = df_filtered[(df_filtered['item_barcode'] == '') | (df_filtered['item_code'] == '')]

                    # Kết nối MySQL
                    conn = mysql.connector.connect(
            host="103.97.126.29",
            user="vvesnzbk_product_data",
            password="Nguyen2004nam@",
            database="vvesnzbk_product_data"
        )
                    cursor = conn.cursor()
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS product_data (
                            item_barcode VARCHAR(50),
                            item_code VARCHAR(50),
                            item_name TEXT,
                            department VARCHAR(255),
                            category VARCHAR(255),
                            sub_category VARCHAR(255),
                            vendor_code VARCHAR(255),
                            vendor_name VARCHAR(255)
                        )
                    """)

                    # Truy vấn tất cả dữ liệu hiện có trong bảng product_data
                    cursor.execute("SELECT item_barcode FROM product_data")
                    existing_barcodes = set(row[0] for row in cursor.fetchall())

                    valid_rows = []
                    for _, row in df_filtered.iterrows():
                        values = [None if pd.isna(v) else v for v in row]
                        if pd.notna(row['item_barcode']) and pd.notna(row['item_code']) and pd.notna(row['item_name']):
                            if row['item_barcode'] not in existing_barcodes:
                                valid_rows.append(values)

                    if valid_rows:
                        cursor.executemany("""
                            INSERT INTO product_data (
                                item_barcode, item_code, item_name,
                                department, category, sub_category,
                                vendor_code, vendor_name
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """, valid_rows)
                    conn.commit()
                    cursor.close()
                    conn.close()
                    messages.success(request, f"Đã import thành công {len(valid_rows)} dòng vào MySQL.")
                except Exception as e:
                    messages.error(request, f"Lỗi import: {e}")
                return redirect('..')
        else:
            form = ItemImportForm()
        context = {
            'form': form,
            'opts': self.model._meta,
            'title': 'Import dữ liệu từ Excel',
        }
        return render(request, 'admin/item_import.html', context)
