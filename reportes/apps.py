"""
Configuración de la aplicación 'reportes'.

Este módulo define la configuración de Django para el módulo de estadísticas,
rankings y reportes de rendimiento del sistema SIGAE.
"""

from django.apps import AppConfig


class ReportesConfig(AppConfig):
    """
    Configuración de la app Reportes.
    
    Gestiona el ciclo de vida y metadatos de la aplicación de reportes.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reportes'

