from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_sm = models.BooleanField(default=False, verbose_name="Quản lý nhóm (is_sm)")
    gmail = models.EmailField(blank=True, null=True, verbose_name="Gmail")

    def __str__(self):
        return f"UserProfile: {self.user.username}"

class Item(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    itembarcode = models.CharField(max_length=100)
    itemname = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField()
    expdate = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def group(self):
        groups = self.user.groups.all()
        return groups[0] if groups else None

    def __str__(self):
        return f"{self.itemname} ({self.itembarcode})"
