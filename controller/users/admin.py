from django.contrib import admin
from .models import *  # Importa todos os modelos

# Users
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role', 'is_active')
    search_fields = ('username', 'email')

admin.site.register(User, UserAdmin)