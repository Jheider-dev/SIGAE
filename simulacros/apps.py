"""
Configuración de la aplicación 'simulacros'.

Este módulo define la configuración de Django para el módulo de gestión
de simulacros, exámenes, preguntas y cálculo de notas del sistema SIGAE.
"""

from django.apps import AppConfig


class SimulacrosConfig(AppConfig):
    """
    Configuración de la app Simulacros.
    
    Gestiona el ciclo de vida y metadatos de la aplicación de simulacros.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'simulacros'

