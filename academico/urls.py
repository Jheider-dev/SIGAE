"""
Rutas de enrutamiento para la aplicación 'academico'.

Mapea las URLs de listado de ciclos académicos y control/escaneo de asistencia QR.
"""

from django.urls import path
from . import views

urlpatterns = [
    path('ciclos/', views.listar_ciclos, name='listar_ciclos'),
    path('ciclos/<int:ciclo_id>/alumnos/', views.gestionar_alumnos_ciclo, name='gestionar_alumnos_ciclo'),
    path('ciclos/<int:ciclo_id>/editar/', views.editar_ciclo, name='editar_ciclo'),
    path('ciclos/<int:ciclo_id>/cambiar-estado/', views.cambiar_estado_ciclo, name='cambiar_estado_ciclo'),
    path('asistencia/', views.control_asistencia, name='control_asistencia'),
    path('asistencia/exportar/csv/', views.exportar_asistencias_csv, name='exportar_asistencias_csv'),
    path('asistencia/docente/registrar/', views.registrar_asistencia_docente, name='registrar_asistencia_docente'),
    path('docente/mis-asistencias/', views.mis_asistencias_docente, name='mis_asistencias_docente'),
    path('liquidacion/', views.ver_liquidacion_docentes, name='ver_liquidacion_docentes'),
    path('liquidacion/exportar/csv/', views.exportar_liquidacion_docentes_csv, name='exportar_liquidacion_docentes_csv'),
    path('pagos/', views.control_pagos, name='control_pagos'),
    path('pagos/registrar/', views.registrar_pago_alumno, name='registrar_pago'),
    path('pagos/registrar/<int:alumno_id>/', views.registrar_pago_alumno, name='registrar_pago_alumno'),
    path('pagos/alumno/<int:alumno_id>/', views.historial_pagos_alumno, name='historial_pagos_alumno'),
    path('pagos/<int:pago_id>/cambiar-estado/', views.cambiar_estado_pago, name='cambiar_estado_pago'),
]
