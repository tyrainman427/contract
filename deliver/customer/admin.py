from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser
from .models import *

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    pass
# Register your models here.
admin.site.register(MenuItem)
admin.site.register(Category)
admin.site.register(OrderModel)
admin.site.register(CartItem)