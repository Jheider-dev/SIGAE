"""
Configuración de la aplicación 'autenticacion'.

Este módulo define la configuración de Django para el módulo de gestión
de usuarios y roles del sistema SIGAE.
"""

from django.apps import AppConfig


class AutenticacionConfig(AppConfig):
    """
    Configuración de la app de Autenticación.
    
    Gestiona el ciclo de vida y metadatos de la aplicación de autenticación.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'autenticacion'

