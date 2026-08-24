"""
Rutas de enrutamiento para la aplicación 'autenticacion'.

Mapea las URLs de login, logout y dashboards específicos por rol de usuario.
"""

from django.urls import path
from . import views

urlpatterns = [
    path('', views.iniciar_sesion, name='raiz'),
    path('login/', views.iniciar_sesion, name='iniciar_sesion'),
    path('logout/', views.cerrar_sesion, name='cerrar_sesion'),
    path('dashboard/admin/', views.dashboard_admin, name='dashboard_admin'),
    path('academico/dashboard-admin/', views.dashboard_admin, name='dashboard_admin_alt'),
    path('dashboard/alumno/', views.dashboard_alumno, name='dashboard_alumno'),
    path('dashboard/docente/', views.dashboard_docente, name='dashboard_docente'),
    path('dashboard/secretaria/', views.dashboard_secretaria, name='dashboard_secretaria'),
    path('perfil/', views.perfil_alumno, name='perfil_alumno'),
    path('alumnos/', views.listar_alumnos, name='listar_alumnos'),
    path('alumnos/exportar/csv/', views.exportar_alumnos_csv, name='exportar_alumnos_csv'),
    path('alumnos/<int:alumno_id>/editar/', views.editar_alumno, name='editar_alumno'),
    path('alumnos/<int:alumno_id>/cambiar-estado/', views.cambiar_estado_alumno, name='cambiar_estado_alumno'),
    path('docentes/', views.listar_docentes, name='listar_docentes'),
    path('docentes/<int:docente_id>/editar/', views.editar_docente, name='editar_docente'),
    path('docentes/<int:docente_id>/cambiar-estado/', views.cambiar_estado_docente, name='cambiar_estado_docente'),
    path('registro/alumno/', views.registrar_alumno, name='registrar_alumno'),
    path('registro/alumno/masivo/', views.registrar_alumno_masivo, name='registrar_alumno_masivo'),
    path('registro/alumno/plantilla/', views.descargar_plantilla_alumnos, name='descargar_plantilla_alumnos'),
    path('registro/docente/', views.registrar_docente, name='registrar_docente'),
    path('api/generar-qr/', views.generar_token_qr_api, name='api_generar_qr'),
]
