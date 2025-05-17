"""
URL configuration for expdate project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from django.conf import settings
from django.conf.urls.static import static

from . import views
from .api import ItemListAPI, ItemDetailAPI, get_item, ExpiringSoonAPI, product_data_api
from .views import api_login

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.login_view, name='default_login'),  # Default to login page
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('home/', views.home_view, name='home'),
    path('logout/', views.logout_view, name='logout'),

    path('delete/<int:item_id>/', views.delete_item_view, name='delete_item'),
    path('edit/<int:item_id>/', views.edit_item_view, name='edit_item'),

    # RESTful API endpoints
    path('api/items/', ItemListAPI.as_view(), name='api_items'),
    path('api/items/<int:item_id>/', ItemDetailAPI.as_view(), name='api_item_detail'),
    path('api/get-item/', get_item, name='get_item'),
    path('api/items/expiring_soon/', ExpiringSoonAPI.as_view(), name='api_expiring_soon'),
    path('api/product-data/', product_data_api, name='api_product_data'),
    path('api/login/', api_login, name='api_login'),

    path('printmode/', views.printmode_view, name='printmode'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

