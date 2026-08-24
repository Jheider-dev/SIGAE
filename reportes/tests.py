from django.test import TestCase
from django.contrib.auth import get_user_model
from simulacros.models import Simulacro, ResultadoSimulacro
from academico.models import Ciclo, Matricula, Aula
from reportes.services import GeneradorReportesService

Usuario = get_user_model()


class SegmentedRankingTestCase(TestCase):
    """
    Prueba que el ranking de mérito consolidado filtre y segmente
    correctamente a los alumnos por su respectiva Área Académica
    (Ingenierías, Biomédicas, Sociales).
    """

    def setUp(self):
        # Crear Ciclo y Aula
        self.ciclo = Ciclo.objects.create(
            nombre="Ordinario 2026-I",
            fecha_inicio="2026-01-01",
            fecha_fin="2026-06-30",
            activo=True
        )
        self.aula = Aula.objects.create(nombre="Salón A", capacidad=40)

        # Crear Alumnos de Ingenierías
        self.alumno_ing1 = Usuario.objects.create_user(
            username="JUANING",
            password="123",
            rol=Usuario.ROL_ALUMNO,
            first_name="Juan",
            last_name="Ingenierias",
            area_academica=Usuario.AREA_INGENIERIAS
        )
        self.alumno_ing2 = Usuario.objects.create_user(
            username="PEDROING",
            password="123",
            rol=Usuario.ROL_ALUMNO,
            first_name="Pedro",
            last_name="Ingenierias",
            area_academica=Usuario.AREA_INGENIERIAS
        )

        # Crear Alumno de Biomédicas
        self.alumno_bio = Usuario.objects.create_user(
            username="MARIABIO",
            password="123",
            rol=Usuario.ROL_ALUMNO,
            first_name="Maria",
            last_name="Biomedicas",
            area_academica=Usuario.AREA_BIOMEDICAS
        )

        # Crear Docente
        self.docente = Usuario.objects.create_user(
            username="PROFESOR",
            password="123",
            rol=Usuario.ROL_DOCENTE,
            first_name="Profesor",
            last_name="Prueba"
        )

        # Matricular Alumnos
        Matricula.objects.create(alumno=self.alumno_ing1, ciclo=self.ciclo, aula=self.aula, codigo_matricula="ING001")
        Matricula.objects.create(alumno=self.alumno_ing2, ciclo=self.ciclo, aula=self.aula, codigo_matricula="ING002")
        Matricula.objects.create(alumno=self.alumno_bio, ciclo=self.ciclo, aula=self.aula, codigo_matricula="BIO001")

        # Crear Simulacro
        self.simulacro = Simulacro.objects.create(
            titulo="Primer Simulacro General",
            fecha="2026-02-15",
            puntaje_maximo=400.00
        )

        # Registrar Resultados
        ResultadoSimulacro.objects.create(alumno=self.alumno_ing1, simulacro=self.simulacro, puntaje_total=250.00)
        ResultadoSimulacro.objects.create(alumno=self.alumno_ing2, simulacro=self.simulacro, puntaje_total=300.00)
        ResultadoSimulacro.objects.create(alumno=self.alumno_bio, simulacro=self.simulacro, puntaje_total=280.00)

    def test_ranking_general(self):
        # El ranking general debe listar a los 3 alumnos ordenados
        ranking_gen = GeneradorReportesService.generar_ranking_merito(self.simulacro.id)
        self.assertEqual(len(ranking_gen), 3)
        self.assertEqual(ranking_gen[0]['username'], 'PEDROING')  # 300 pts
        self.assertEqual(ranking_gen[1]['username'], 'MARIABIO')  # 280 pts
        self.assertEqual(ranking_gen[2]['username'], 'JUANING')   # 250 pts

    def test_ranking_filtrado_ingenierias(self):
        # El ranking de Ingenierías solo debe listar a juan y pedro
        ranking_ing = GeneradorReportesService.generar_ranking_merito(
            self.simulacro.id,
            area_academica=Usuario.AREA_INGENIERIAS
        )
        self.assertEqual(len(ranking_ing), 2)
        # Debe conservar el orden correcto descendente
        self.assertEqual(ranking_ing[0]['username'], 'PEDROING')  # 300 pts (puesto 1 en su área)
        self.assertEqual(ranking_ing[1]['username'], 'JUANING')   # 250 pts (puesto 2 en su área)

    def test_ranking_filtrado_biomedicas(self):
        # El ranking de Biomédicas solo debe listar a maria
        ranking_bio = GeneradorReportesService.generar_ranking_merito(
            self.simulacro.id,
            area_academica=Usuario.AREA_BIOMEDICAS
        )
        self.assertEqual(len(ranking_bio), 1)
        self.assertEqual(ranking_bio[0]['username'], 'MARIABIO')  # 280 pts

    def test_docente_ver_reporte_notas(self):
        from django.urls import reverse
        self.client.login(username="PROFESOR", password="123")
        response = self.client.get(reverse('ver_reporte_notas', args=[self.simulacro.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'reportes/reporte_notas.html')
        self.assertContains(response, 'ING002')
        self.assertContains(response, 'BIO001')

    def test_alumno_restringido_reporte_notas(self):
        from django.urls import reverse
        self.client.login(username="JUANING", password="123")
        response = self.client.get(reverse('ver_reporte_notas', args=[self.simulacro.id]))
        # Alumno debe ser redirigido con error
        self.assertEqual(response.status_code, 302)
