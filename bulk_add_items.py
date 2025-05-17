import os
import django
from datetime import date, timedelta

# Thiết lập biến môi trường cho Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'expdate.settings')
django.setup()

from expdate.models import Item
from django.contrib.auth.models import User

users = User.objects.all()

for user in users:
    items = []
    today = date.today()
    # 34 sản phẩm đã hết hạn
    for i in range(34):
        items.append(Item(
            user=user,
            itembarcode=f"BAR{user.id:03d}E{i:03d}",
            itemname=f"SP_{user.username}_expired_{i}",
            quantity=1,
            expdate=today - timedelta(days=1 + i)  # đã hết hạn
        ))
    # 33 sản phẩm sắp hết hạn (1-7 ngày tới)
    for i in range(33):
        items.append(Item(
            user=user,
            itembarcode=f"BAR{user.id:03d}X{i:03d}",
            itemname=f"SP_{user.username}_expiring_{i}",
            quantity=1,
            expdate=today + timedelta(days=1 + (i % 7))  # sắp hết hạn (1-7 ngày tới)
        ))
    # 33 sản phẩm còn hạn (>=8 ngày tới)
    for i in range(33):
        items.append(Item(
            user=user,
            itembarcode=f"BAR{user.id:03d}V{i:03d}",
            itemname=f"SP_{user.username}_valid_{i}",
            quantity=1,
            expdate=today + timedelta(days=8 + i)  # còn hạn
        ))
    Item.objects.bulk_create(items)
print("Done!")
