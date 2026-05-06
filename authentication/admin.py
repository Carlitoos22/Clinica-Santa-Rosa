from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('username', 'dni', 'first_name', 'last_name', 'rol', 'is_active')
    list_filter = ('rol', 'is_active')
    search_fields = ('username', 'dni', 'first_name', 'last_name')
    fieldsets = UserAdmin.fieldsets + (
        ('Datos Clínica', {'fields': ('rol', 'dni', 'celular')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Datos Clínica', {'fields': ('rol', 'dni', 'celular')}),
    )
