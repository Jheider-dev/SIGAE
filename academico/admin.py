"""
Configuración del Panel de Administración para la aplicación 'academico'.

Registra los modelos Ciclo, Aula, Matricula y AsistenciaQR con
configuraciones de visualización, filtros y búsquedas en el admin de Django.
"""

from django.contrib import admin
from .models import Ciclo, Aula, Matricula, AsistenciaQR, AsistenciaDocente


@admin.register(Ciclo)
class CicloAdmin(admin.ModelAdmin):
    """
    Configuración administrativa para el modelo Ciclo.
    """
    list_display = ('nombre', 'fecha_inicio', 'fecha_fin', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre',)


@admin.register(Aula)
class AulaAdmin(admin.ModelAdmin):
    """
    Configuración administrativa para el modelo Aula.
    """
    list_display = ('nombre', 'capacidad')
    search_fields = ('nombre',)


@admin.register(Matricula)
class MatriculaAdmin(admin.ModelAdmin):
    """
    Configuración administrativa para el modelo Matricula.
    """
    list_display = ('codigo_matricula', 'alumno', 'ciclo', 'aula', 'activo', 'fecha_matricula')
    list_filter = ('activo', 'ciclo', 'aula')
    search_fields = ('codigo_matricula', 'alumno__username', 'alumno__first_name', 'alumno__last_name')


@admin.register(AsistenciaQR)
class AsistenciaQRAdmin(admin.ModelAdmin):
    """
    Configuración administrativa para el modelo AsistenciaQR.
    """
    list_display = ('alumno', 'fecha', 'hora_acceso', 'estado')
    list_filter = ('estado', 'fecha')
    search_fields = ('alumno__username', 'alumno__first_name', 'alumno__last_name')


@admin.register(AsistenciaDocente)
class AsistenciaDocenteAdmin(admin.ModelAdmin):
    """
    Configuración administrativa para el modelo AsistenciaDocente.
    """
    list_display = ('docente', 'fecha', 'hora_acceso', 'horas_dictadas')
    list_filter = ('fecha',)
    search_fields = ('docente__username', 'docente__first_name', 'docente__last_name')
