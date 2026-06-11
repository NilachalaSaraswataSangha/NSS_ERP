from django.contrib import admin

from .models import Role
from .models import UserRole


admin.site.register(Role)
admin.site.register(UserRole)