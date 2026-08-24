"""
Configuración del Panel de Administración para la aplicación 'autenticacion'.

Registra el modelo de usuario personalizado Usuario heredando de UserAdmin
para una gestión de credenciales y roles segura y estructurada.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    """
    Configuración administrativa para el modelo Usuario.
    
    Extiende la visualización y edición del panel administrativo de Django
    para incorporar los campos personalizados de rol, teléfono y dirección.
    """
    list_display = ('username', 'email', 'first_name', 'last_name', 'rol', 'is_staff', 'is_active')
    list_filter = ('rol', 'is_staff', 'is_active')
    
    # Agregar campos personalizados a los formularios de edición y adición
    fieldsets = UserAdmin.fieldsets + (
        ('Información de Rol y Contacto', {'fields': ('rol', 'telefono', 'direccion')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Información de Rol y Contacto', {
            'fields': ('rol', 'telefono', 'direccion'),
        }),
    )
