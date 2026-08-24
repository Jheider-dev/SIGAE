"""
Rutas de enrutamiento para la aplicación 'reportes'.

Mapea las URLs de ranking de mérito y de endpoints de estadísticas en formato JSON.
"""

from django.urls import path
from . import views

urlpatterns = [
    path('simulacros/<int:simulacro_id>/ranking/', views.ver_ranking_html, name='ver_ranking_html'),
    path('simulacros/<int:simulacro_id>/reporte-notas/', views.ver_reporte_notas, name='ver_reporte_notas'),
    path('api/simulacros/<int:simulacro_id>/ranking/', views.ver_ranking_simulacro, name='api_ranking_simulacro'),
    path('api/simulacros/<int:simulacro_id>/stats/', views.ver_estadisticas_simulacro, name='api_stats_simulacro'),
    path('api/ciclos/<int:ciclo_id>/stats/', views.ver_estadisticas_ciclo, name='api_stats_ciclo'),
]
