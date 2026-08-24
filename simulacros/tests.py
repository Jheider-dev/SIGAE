from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from .models import Simulacro, Pregunta

Usuario = get_user_model()


class SimulacroParserTestCase(TestCase):
    """
    Prueba la carga de preguntas y claves de simulacros
    a partir de archivos CSV/TXT usando el parser de texto plano.
    """

    def setUp(self):
        # Crear docente para iniciar sesión
        self.docente = Usuario.objects.create_user(
            username="CARLOSMF",
            password="password123",
            rol=Usuario.ROL_DOCENTE,
            first_name="Carlos",
            last_name="Mamani"
        )
        self.client.login(username="CARLOSMF", password="password123")

    def test_parser_csv_valido(self):
        # Simulamos archivo en formato CSV con punto y coma
        file_content = (
            "Numero;Enunciado;A;B;C;D;E;Correcta\n"
            "1;¿Cuál es 2+2?;3;4;5;6;7;B\n"
            "2;¿Cuál es la capital de Perú?;Puno;Cusco;Lima;Tacna;Arequipa;C\n"
        )
        csv_file = SimpleUploadedFile(
            "claves.csv",
            file_content.encode('utf-8'),
            content_type="text/csv"
        )

        response = self.client.post(
            reverse('crear_simulacro_claves'),
            {
                'titulo': 'Simulacro de Prueba Parser',
                'fecha': '2026-08-15',
                'puntaje_maximo': '400.00',
                'descripcion': 'Examen de prueba',
                'puntaje_correcta': '4.00',
                'puntaje_incorrecta': '0.00',  # Sin penalización
                'puntaje_omitida': '0.00',
                'archivo': csv_file
            }
        )

        # Debe redirigir al panel del docente
        self.assertEqual(response.status_code, 302)

        # Verificar existencia en DB
        sim = Simulacro.objects.filter(titulo='Simulacro de Prueba Parser').first()
        self.assertIsNotNone(sim)

        # Verificar preguntas creadas
        preguntas = Pregunta.objects.filter(simulacro=sim).order_by('numero_pregunta')
        self.assertEqual(preguntas.count(), 2)
        
        # Verificar detalles de la pregunta 1
        preg1 = preguntas[0]
        self.assertEqual(preg1.numero_pregunta, 1)
        self.assertEqual(preg1.enunciado, "¿Cuál es 2+2?")
        self.assertEqual(preg1.alternativa_correcta, "B")
        self.assertEqual(float(preg1.puntaje_correcta), 4.00)
        self.assertEqual(float(preg1.puntaje_incorrecta), 0.00)  # Sin penalización

        # Verificar detalles de la pregunta 2
        preg2 = preguntas[1]
        self.assertEqual(preg2.numero_pregunta, 2)
        self.assertEqual(preg2.enunciado, "¿Cuál es la capital de Perú?")
        self.assertEqual(preg2.alternativa_correcta, "C")


class SimulacroAreaRestrictionTestCase(TestCase):
    """
    Prueba las restricciones de ingreso a simulacros
    según el área académica de los alumnos.
    """

    def setUp(self):
        # Crear alumnos con distintas áreas
        self.alumno_ing = Usuario.objects.create_user(
            username="JAIMEING",
            password="123",
            rol=Usuario.ROL_ALUMNO,
            area_academica=Usuario.AREA_INGENIERIAS
        )
        self.alumno_bio = Usuario.objects.create_user(
            username="MARIABIO",
            password="123",
            rol=Usuario.ROL_ALUMNO,
            area_academica=Usuario.AREA_BIOMEDICAS
        )

        # Crear simulacro de Ingenierías
        self.simulacro_ing = Simulacro.objects.create(
            titulo="Simulacro Ingenierías",
            fecha="2026-08-20",
            area_academica=Simulacro.AREA_INGENIERIAS,
            activo=True
        )

    def test_listar_simulacros_por_area(self):
        # Alumno Ingenierías debe ver el simulacro de Ingenierías
        self.client.login(username="JAIMEING", password="123")
        response = self.client.get(reverse('listar_simulacros'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Simulacro Ingenierías")

        # Alumno Biomédicas no debe ver el simulacro de Ingenierías
        self.client.login(username="MARIABIO", password="123")
        response2 = self.client.get(reverse('listar_simulacros'))
        self.assertEqual(response2.status_code, 200)
        self.assertNotContains(response2, "Simulacro Ingenierías")

    def test_rendir_simulacro_restringido(self):
        # Alumno de Biomédicas intenta entrar a un simulacro de Ingenierías
        self.client.login(username="MARIABIO", password="123")
        response = self.client.get(reverse('rendir_simulacro', args=[self.simulacro_ing.id]))
        # Debe redirigirlo con acceso denegado
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('listar_simulacros'))

        # Alumno de Ingenierías entra a su propio simulacro
        self.client.login(username="JAIMEING", password="123")
        response2 = self.client.get(reverse('rendir_simulacro', args=[self.simulacro_ing.id]))
        self.assertEqual(response2.status_code, 200)

    def test_listar_simulacros_pendientes_vs_historial(self):
        # JAIMEING no ha rendido el simulacro, debe estar en activos y no en historial
        self.client.login(username="JAIMEING", password="123")
        response = self.client.get(reverse('listar_simulacros'))
        self.assertEqual(len(response.context['simulacros_activos']), 1)
        self.assertEqual(len(response.context['historial_rendidos']), 0)

        # JAIMEING rinde el simulacro
        from .models import ResultadoSimulacro
        ResultadoSimulacro.objects.create(
            alumno=self.alumno_ing,
            simulacro=self.simulacro_ing,
            puntaje_total=280.50
        )

        # Ahora debe estar en historial y no en activos
        response2 = self.client.get(reverse('listar_simulacros'))
        self.assertEqual(len(response2.context['simulacros_activos']), 0)
        self.assertEqual(len(response2.context['historial_rendidos']), 1)
        self.assertContains(response2, "Historial de Simulacros Rendidos")


class PlantillaSimulacroCSVTestCase(TestCase):
    """
    Prueba la generación y descarga de la plantilla CSV de simulacros con 8 columnas.
    """

    def setUp(self):
        self.docente = Usuario.objects.create_user(
            username="DOC_CSV",
            password="123",
            rol=Usuario.ROL_DOCENTE
        )

    def test_descargar_plantilla_simulacro_csv(self):
        self.client.login(username="DOC_CSV", password="123")
        response = self.client.get(reverse('descargar_plantilla_simulacro'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn('attachment; filename="plantilla_simulacro_sigae.csv"', response['Content-Disposition'])
        content = response.content.decode('utf-8')
        self.assertIn('NroPregunta;Enunciado;AlternativaA;AlternativaB;AlternativaC;AlternativaD;AlternativaE;AlternativaCorrecta', content)


class DashboardDocenteMetricasTestCase(TestCase):
    """
    Prueba las métricas de horas acumuladas y el filtrado de simulacros en el dashboard del docente.
    """

    def setUp(self):
        self.docente = Usuario.objects.create_user(
            username="DOC_METRICA",
            password="123",
            rol=Usuario.ROL_DOCENTE,
            curso_asignado="Álgebra",
            precio_hora=35.00
        )
        self.otro_docente = Usuario.objects.create_user(
            username="DOC_OTRO",
            password="123",
            rol=Usuario.ROL_DOCENTE,
            curso_asignado="Física"
        )

    def test_dashboard_metricas_horas_y_simulacros_filtrados(self):
        import datetime
        from academico.models import AsistenciaDocente
        hoy = datetime.date.today()

        # Registrar asistencias para este docente en el mes actual
        AsistenciaDocente.objects.create(
            docente=self.docente,
            horas_dictadas=2.0,
            codigo_qr_escaneado="QR1"
        )
        AsistenciaDocente.objects.create(
            docente=self.docente,
            horas_dictadas=1.5,
            codigo_qr_escaneado="QR2"
        )

        # Crear simulacro de Álgebra por este docente
        sim1 = Simulacro.objects.create(
            titulo="Simulacro de Álgebra I",
            fecha=hoy,
            docente=self.docente,
            activo=True
        )
        # Crear simulacro de Física por el otro docente
        sim2 = Simulacro.objects.create(
            titulo="Simulacro de Física General",
            fecha=hoy,
            docente=self.otro_docente,
            activo=True
        )

        self.client.login(username="DOC_METRICA", password="123")
        response = self.client.get(reverse('dashboard_docente'))
        self.assertEqual(response.status_code, 200)

        # Verificar horas acumuladas = 3.5
        self.assertEqual(response.context['total_horas'], 3.5)
        self.assertEqual(response.context['total_sesiones'], 2)

        # Verificar que solo ve el simulacro de Álgebra
        simulacros_visibles = response.context['simulacros']
        self.assertIn(sim1, simulacros_visibles)
        self.assertNotIn(sim2, simulacros_visibles)


