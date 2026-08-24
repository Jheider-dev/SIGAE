"""
Vistas para la aplicación 'reportes'.

Define controladores para retornar en formato JSON los rankings y estadísticas
académicas calculadas dinámicamente por la capa de servicios de SIGAE.
"""

from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from simulacros.models import Simulacro
from .services import GeneradorReportesService


def ver_ranking_simulacro(request, simulacro_id):
    """
    Controlador para retornar el ranking de mérito de un simulacro en formato JSON.

    Args:
        request: Objeto HttpRequest de Django.
        simulacro_id (int): Identificador del simulacro a consultar.

    Returns:
        JsonResponse: Respuesta JSON conteniendo la lista de posiciones ordenada.
    """
    ranking = GeneradorReportesService.generar_ranking_merito(simulacro_id)
    return JsonResponse({'ranking': ranking}, safe=False)


def ver_estadisticas_simulacro(request, simulacro_id):
    """
    Controlador para retornar estadísticas generales de notas de un simulacro.

    Args:
        request: Objeto HttpRequest de Django.
        simulacro_id (int): Identificador del simulacro a consultar.

    Returns:
        JsonResponse: Respuesta JSON con cantidad de participantes, promedio,
                      máxima y mínima de notas.
    """
    stats = GeneradorReportesService.calcular_estadisticas_simulacro(simulacro_id)
    return JsonResponse(stats)


def ver_estadisticas_ciclo(request, ciclo_id):
    """
    Controlador para retornar estadísticas agregadas de notas en un ciclo.

    Args:
        request: Objeto HttpRequest de Django.
        ciclo_id (int): Identificador del ciclo académico.

    Returns:
        JsonResponse: Respuesta JSON con promedios y notas extremas históricas.
    """
    stats = GeneradorReportesService.calcular_estadisticas_ciclo(ciclo_id)
    return JsonResponse(stats)


@login_required(login_url='iniciar_sesion')
def ver_ranking_html(request, simulacro_id):
    """
    Controlador para renderizar el ranking de mérito y las estadísticas
    generales de un simulacro en una plantilla HTML.
    Segmenta estrictamente por Área Académica si es Alumno, y permite filtrar
    a otros roles.
    """
    simulacro = get_object_or_404(Simulacro, id=simulacro_id)
    
    # Por defecto, ver todo el ranking si no es alumno
    area_filtro = request.GET.get('area', '').upper()
    
    if request.user.rol == 'ALUMNO':
        # Los alumnos tienen estrictamente filtrado el ranking por su propia área
        area_filtro = request.user.area_academica or 'INGENIERIAS'
        
    if area_filtro not in ['INGENIERIAS', 'BIOMEDICAS', 'SOCIALES']:
        area_filtro = None

    ranking = GeneradorReportesService.generar_ranking_merito(simulacro_id, area_academica=area_filtro)
    stats = GeneradorReportesService.calcular_estadisticas_simulacro(simulacro_id)

    # Si es alumno, queremos marcar su posición en el ranking filtrado
    # Para destacar su fila
    alumno_username = request.user.username if request.user.rol == 'ALUMNO' else None

    # Áreas para el selector administrativo
    areas_list = [
        ('INGENIERIAS', 'Ingenierías'),
        ('BIOMEDICAS', 'Biomédicas'),
        ('SOCIALES', 'Sociales')
    ]

    contexto = {
        'simulacro': simulacro,
        'ranking': ranking,
        'stats': stats,
        'area_filtro': area_filtro,
        'areas_list': areas_list,
        'alumno_username': alumno_username
    }
    return render(request, 'reportes/ver_ranking.html', contexto)


@login_required(login_url='iniciar_sesion')
def ver_reporte_notas(request, simulacro_id):
    """
    Vista de reporte de notas de un simulacro, exclusivo para Docentes y Administradores.
    Muestra una tabla con todos los estudiantes y sus puntajes.
    """
    if request.user.rol not in ['DOCENTE', 'SECRETARIA'] and not request.user.is_superuser and not request.user.is_staff:
        from django.contrib import messages
        messages.error(request, "Acceso restringido a Docentes y Personal Administrativo.")
        return redirect('raiz')

    simulacro = get_object_or_404(Simulacro, id=simulacro_id)
    
    # Permitir filtrar el reporte por área
    area_filtro = request.GET.get('area', '').upper()
    if area_filtro not in ['INGENIERIAS', 'BIOMEDICAS', 'SOCIALES']:
        area_filtro = None

    ranking = GeneradorReportesService.generar_ranking_merito(simulacro_id, area_academica=area_filtro)
    stats = GeneradorReportesService.calcular_estadisticas_simulacro(simulacro_id)

    areas_list = [
        ('INGENIERIAS', 'Ingenierías'),
        ('BIOMEDICAS', 'Biomédicas'),
        ('SOCIALES', 'Sociales')
    ]

    contexto = {
        'simulacro': simulacro,
        'ranking': ranking,
        'stats': stats,
        'area_filtro': area_filtro,
        'areas_list': areas_list
    }
    return render(request, 'reportes/reporte_notas.html', contexto)

