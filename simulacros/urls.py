"""
Rutas de enrutamiento para la aplicación 'simulacros'.

Mapea las URLs de listado de simulacros, la pantalla de examen y el procesamiento de respuestas.
"""

from django.urls import path
from . import views

urlpatterns = [
    path('simulacros/', views.listar_simulacros, name='listar_simulacros'),
    path('simulacros/admin/', views.listar_simulacros_admin, name='listar_simulacros_admin'),
    path('simulacros/crear/', views.subir_simulacro_claves, name='crear_simulacro_claves'),
    path('simulacros/plantilla/', views.descargar_plantilla_simulacro, name='descargar_plantilla_simulacro'),
    path('simulacros/<int:simulacro_id>/rendir/', views.rendir_simulacro, name='rendir_simulacro'),
    path('simulacros/<int:simulacro_id>/procesar/', views.procesar_respuestas, name='procesar_respuestas'),
    path('simulacros/<int:simulacro_id>/revision/', views.ver_revision_simulacro, name='ver_revision_simulacro'),
    path('simulacros/<int:simulacro_id>/revision/<int:alumno_id>/', views.ver_revision_simulacro, name='ver_revision_simulacro_alumno'),
    path('simulacros/<int:simulacro_id>/exportar/csv/', views.exportar_ranking_simulacro_csv, name='exportar_ranking_simulacro_csv'),
]
