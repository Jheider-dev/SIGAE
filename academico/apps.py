"""
Configuración de la aplicación 'academico'.

Este módulo define la configuración de Django para el módulo de gestión
académica (ciclos, matrículas y asignación de aulas) del sistema SIGAE.
"""

from django.apps import AppConfig


class AcademicoConfig(AppConfig):
    """
    Configuración de la app Académico.
    
    Gestiona el ciclo de vida y metadatos de la aplicación académica.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'academico'

