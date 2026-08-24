"""
Servicios de negocio para la aplicación 'reportes'.

Define la lógica analítica para el cálculo de estadísticas académicas, promedios
y la generación del ranking de mérito para la Academia Preuniversitaria Euler.
"""

from django.db.models import Avg, Max, Min, Count
from simulacros.models import Simulacro, ResultadoSimulacro
from academico.models import Ciclo, Matricula


class GeneradorReportesService:
    """
    Servicio encargado de procesar y consolidar la información académica.

    Proporciona métodos estáticos para el cálculo de indicadores de rendimiento
    y ordenamiento de postulantes en rankings de mérito.
    """

    @staticmethod
    def calcular_estadisticas_simulacro(simulacro_id: int) -> dict:
        """
        Calcula estadísticas generales de notas para un simulacro específico.

        Args:
            simulacro_id (int): Identificador único del simulacro.

        Returns:
            dict: Diccionario conteniendo:
                - total_participantes (int): Cantidad de alumnos evaluados.
                - puntaje_promedio (float): Promedio de notas obtenidas.
                - puntaje_maximo (float): Nota más alta registrada.
                - puntaje_minimo (float): Nota más baja registrada.
        """
        # Verificar existencia del simulacro
        if not Simulacro.objects.filter(id=simulacro_id).exists():
            return {
                'total_participantes': 0,
                'puntaje_promedio': 0.00,
                'puntaje_maximo': 0.00,
                'puntaje_minimo': 0.00
            }

        resultados = ResultadoSimulacro.objects.filter(simulacro_id=simulacro_id)
        stats = resultados.aggregate(
            promedio=Avg('puntaje_total'),
            maximo=Max('puntaje_total'),
            minimo=Min('puntaje_total'),
            total=Count('id')
        )

        return {
            'total_participantes': stats['total'] or 0,
            'puntaje_promedio': round(float(stats['promedio']), 2) if stats['promedio'] is not None else 0.00,
            'puntaje_maximo': float(stats['maximo']) if stats['maximo'] is not None else 0.00,
            'puntaje_minimo': float(stats['minimo']) if stats['minimo'] is not None else 0.00
        }

    @staticmethod
    def calcular_estadisticas_ciclo(ciclo_id: int) -> dict:
        """
        Calcula las estadísticas acumuladas de todos los simulacros rendidos
        por los alumnos matriculados en un ciclo académico específico.

        Args:
            ciclo_id (int): Identificador único del ciclo académico.

        Returns:
            dict: Diccionario conteniendo:
                - total_evaluaciones (int): Cantidad de exámenes rendidos.
                - puntaje_promedio (float): Promedio general del ciclo.
                - puntaje_maximo (float): Nota máxima histórica en el ciclo.
                - puntaje_minimo (float): Nota mínima histórica en el ciclo.
        """
        # Verificar existencia del ciclo
        if not Ciclo.objects.filter(id=ciclo_id).exists():
            return {
                'total_evaluaciones': 0,
                'puntaje_promedio': 0.00,
                'puntaje_maximo': 0.00,
                'puntaje_minimo': 0.00
            }

        # Filtrar resultados de alumnos matriculados activamente en este ciclo
        resultados = ResultadoSimulacro.objects.filter(
            alumno__matriculas__ciclo_id=ciclo_id,
            alumno__matriculas__activo=True
        )

        stats = resultados.aggregate(
            promedio=Avg('puntaje_total'),
            maximo=Max('puntaje_total'),
            minimo=Min('puntaje_total'),
            total=Count('id')
        )

        return {
            'total_evaluaciones': stats['total'] or 0,
            'puntaje_promedio': round(float(stats['promedio']), 2) if stats['promedio'] is not None else 0.00,
            'puntaje_maximo': float(stats['maximo']) if stats['maximo'] is not None else 0.00,
            'puntaje_minimo': float(stats['minimo']) if stats['minimo'] is not None else 0.00
        }

    @staticmethod
    def generar_ranking_merito(simulacro_id: int, area_academica: str = None) -> list:
        """
        Genera una lista ordenada descendente (ranking) de los alumnos
        que rindieron un simulacro específico, opcionalmente filtrado por Área Académica.

        Args:
            simulacro_id (int): Identificador único del simulacro.
            area_academica (str): Área por la cual filtrar (INGENIERIAS, BIOMEDICAS, SOCIALES).

        Returns:
            list: Lista de diccionarios con la estructura de ranking.
        """
        resultados = ResultadoSimulacro.objects.filter(
            simulacro_id=simulacro_id
        ).select_related('alumno')

        if area_academica:
            resultados = resultados.filter(alumno__area_academica=area_academica)

        resultados = resultados.order_by('-puntaje_total')

        ranking = []
        for index, res in enumerate(resultados, start=1):
            # Obtener matrícula activa en cualquier ciclo para extraer el código
            matricula_activa = Matricula.objects.filter(
                alumno=res.alumno,
                activo=True
            ).first()
            
            codigo = matricula_activa.codigo_matricula if matricula_activa else "SIN MATRÍCULA"

            ranking.append({
                'puesto': index,
                'codigo_alumno': codigo,
                'username': res.alumno.username,
                'nombre_completo': res.alumno.get_full_name() or res.alumno.username,
                'respuestas_correctas': res.respuestas_correctas,
                'respuestas_incorrectas': res.respuestas_incorrectas,
                'respuestas_omitidas': res.respuestas_omitidas,
                'puntaje_total': float(res.puntaje_total),
                'area_academica': res.alumno.get_area_academica_display() if res.alumno.area_academica else "No asignada"
            })

        return ranking
