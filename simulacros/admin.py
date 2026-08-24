"""
Configuración del Panel de Administración para la aplicación 'simulacros'.

Registra los modelos Simulacro, Pregunta, ResultadoSimulacro y DetalleRespuesta
con visualizaciones estructuradas para gestionar los exámenes de Euler.
"""

from django.contrib import admin
from .models import Simulacro, Pregunta, ResultadoSimulacro, DetalleRespuesta


@admin.register(Simulacro)
class SimulacroAdmin(admin.ModelAdmin):
    """
    Configuración administrativa para el modelo Simulacro.
    """
    list_display = ('titulo', 'fecha', 'puntaje_maximo', 'activo')
    list_filter = ('activo', 'fecha')
    search_fields = ('titulo',)


@admin.register(Pregunta)
class PreguntaAdmin(admin.ModelAdmin):
    """
    Configuración administrativa para el modelo Pregunta.
    """
    list_display = ('numero_pregunta', 'simulacro', 'enunciado_corto', 'alternativa_correcta')
    list_filter = ('simulacro', 'alternativa_correcta')
    search_fields = ('enunciado',)

    def enunciado_corto(self, obj):
        """
        Retorna los primeros 60 caracteres del enunciado para visualización en tablas.

        Args:
            obj (Pregunta): Instancia de la pregunta.

        Returns:
            str: Fragmento corto del enunciado.
        """
        return obj.enunciado[:60] + '...' if len(obj.enunciado) > 60 else obj.enunciado
    enunciado_corto.short_description = "Enunciado"


@admin.register(ResultadoSimulacro)
class ResultadoSimulacroAdmin(admin.ModelAdmin):
    """
    Configuración administrativa para el modelo ResultadoSimulacro.
    """
    list_display = (
        'alumno',
        'simulacro',
        'puntaje_total',
        'respuestas_correctas',
        'respuestas_incorrectas',
        'respuestas_omitidas'
    )
    list_filter = ('simulacro',)
    search_fields = ('alumno__username', 'alumno__first_name', 'alumno__last_name', 'simulacro__titulo')


@admin.register(DetalleRespuesta)
class DetalleRespuestaAdmin(admin.ModelAdmin):
    """
    Configuración administrativa para el modelo DetalleRespuesta.
    """
    list_display = ('resultado', 'pregunta', 'alternativa_marcada', 'puntaje_obtenido')
    list_filter = ('resultado__simulacro', 'alternativa_marcada')
