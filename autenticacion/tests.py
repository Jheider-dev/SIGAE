from django.test import TestCase
from django.contrib.auth import get_user_model
from .utils import generar_username_unico, generar_token_qr, verificar_token_qr
import time

Usuario = get_user_model()


class UsernameGenerationTestCase(TestCase):
    """
    Prueba el algoritmo de generación automática de usernames
    y la resolución de colisiones (homonimia).
    """

    def test_generar_username_simple(self):
        username = generar_username_unico("Jaime Rolando", "Perez Condori")
        self.assertEqual(username, "JAIMEPC")

    def test_generar_username_colision(self):
        # Crear primer usuario
        Usuario.objects.create_user(
            username="JAIMEPC",
            password="password123",
            rol=Usuario.ROL_ALUMNO
        )

        # Generar para otro con mismos datos
        username2 = generar_username_unico("Jaime Rolando", "Perez Condori")
        self.assertEqual(username2, "JAIMEPC1")

        # Crear segundo usuario
        Usuario.objects.create_user(
            username="JAIMEPC1",
            password="password123",
            rol=Usuario.ROL_ALUMNO
        )

        # Generar tercero
        username3 = generar_username_unico("Jaime Rolando", "Perez Condori")
        self.assertEqual(username3, "JAIMEPC2")


class TokenQRTestCase(TestCase):
    """
    Prueba el generador y verificador de tokens QR dinámicos
    con firma HMAC-SHA256 y expiración temporal.
    """

    def setUp(self):
        self.alumno = Usuario.objects.create_user(
            username="PEDROFL",
            password="password123",
            rol=Usuario.ROL_ALUMNO,
            dni="12345678"
        )

    def test_verificar_token_valido(self):
        token = generar_token_qr(self.alumno)
        es_valido, res = verificar_token_qr(token, max_age_seconds=15)
        self.assertTrue(es_valido)
        self.assertEqual(res, self.alumno)

    def test_verificar_token_expirado(self):
        # Generar token
        token = generar_token_qr(self.alumno)
        
        # Simular espera de 16 segundos
        # Para evitar sleep real lento en tests, manipulamos el token restándole 20 segundos
        parts = token.split('|')
        old_timestamp = int(parts[3]) - 20
        # Re-firmar
        import hmac, hashlib
        from django.conf import settings
        message = f"{parts[1]}|{parts[2]}|{old_timestamp}"
        new_sig = hmac.new(
            settings.SECRET_KEY.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        expired_token = f"SIGAE|{parts[1]}|{parts[2]}|{old_timestamp}|{new_sig}"
        
        es_valido, res = verificar_token_qr(expired_token, max_age_seconds=15)
        self.assertFalse(es_valido)
        self.assertIn("expirado", res.lower())

    def test_verificar_token_firma_invalida(self):
        token = generar_token_qr(self.alumno)
        # Modificar firma
        parts = token.split('|')
        parts[4] = "firmafalsade32caracteresymuchomas"
        tampered_token = "|".join(parts)
        
        es_valido, res = verificar_token_qr(tampered_token, max_age_seconds=15)
        self.assertFalse(es_valido)
        self.assertIn("firma", res.lower())


class RegistrarAlumnoMasivoTestCase(TestCase):
    """
    Prueba el registro masivo de alumnos mediante archivos CSV/TXT.
    """

    def setUp(self):
        # Crear secretaria
        self.secretaria = Usuario.objects.create_user(
            username="SECRE1",
            password="123",
            rol=Usuario.ROL_SECRETARIA
        )

    def test_registro_masivo_exitoso(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.urls import reverse

        self.client.login(username="SECRE1", password="123")

        # Archivo CSV de prueba con 2 alumnos válidos y 1 inválido (área incorrecta)
        csv_data = (
            "Nombres,Apellidos,DNI,Area Academica,Telefono,Direccion,Email\n"
            "Juan Carlos,Perez Quispe,87654321,INGENIERIAS,951111111,Jr. Puno 123,juan@mail.com\n"
            "Maria Helena,Luna Gomez,98765432,BIOMEDICAS,,,\n"
            "Invalido,Alumno,11111111,ARTE,,,\n"
        )
        archivo_csv = SimpleUploadedFile("alumnos.csv", csv_data.encode('utf-8'), content_type="text/csv")

        response = self.client.post(
            reverse('registrar_alumno_masivo'),
            {'archivo_alumnos': archivo_csv}
        )
        self.assertEqual(response.status_code, 302)

        # Verificar que los 2 alumnos válidos fueron creados
        self.assertTrue(Usuario.objects.filter(dni="87654321").exists())
        self.assertTrue(Usuario.objects.filter(dni="98765432").exists())
        # El inválido no debe existir
        self.assertFalse(Usuario.objects.filter(dni="11111111").exists())

        # Verificar el username autogenerado
        alumno1 = Usuario.objects.get(dni="87654321")
        self.assertEqual(alumno1.username, "JUANPQ")
        self.assertEqual(alumno1.rol, Usuario.ROL_ALUMNO)
        self.assertEqual(alumno1.area_academica, Usuario.AREA_INGENIERIAS)


class SecretariaPermisosTestCase(TestCase):
    """
    Verifica que el rol de Secretaría no pueda acceder a registrar docente,
    quedando reservado exclusivamente para Administradores/Staff.
    """

    def setUp(self):
        self.secretaria = Usuario.objects.create_user(
            username="SECRE_TEST",
            password="123",
            rol=Usuario.ROL_SECRETARIA
        )
        self.admin = Usuario.objects.create_superuser(
            username="ADMIN_TEST",
            password="123",
            email="admin@test.com"
        )

    def test_secretaria_no_puede_acceder_a_registrar_docente(self):
        from django.urls import reverse
        self.client.login(username="SECRE_TEST", password="123")
        response = self.client.get(reverse('registrar_docente'))
        # Debe redirigir con error
        self.assertEqual(response.status_code, 302)

    def test_admin_si_puede_acceder_a_registrar_docente(self):
        from django.urls import reverse
        self.client.login(username="ADMIN_TEST", password="123")
        response = self.client.get(reverse('registrar_docente'))
        self.assertEqual(response.status_code, 200)


class PlantillaCSVTestCase(TestCase):
    """
    Prueba la generación y descarga de la plantilla CSV de ejemplo.
    """

    def setUp(self):
        self.secretaria = Usuario.objects.create_user(
            username="SECRE_CSV",
            password="123",
            rol=Usuario.ROL_SECRETARIA
        )

    def test_descargar_plantilla_csv(self):
        from django.urls import reverse
        self.client.login(username="SECRE_CSV", password="123")
        response = self.client.get(reverse('descargar_plantilla_alumnos'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn('attachment; filename="plantilla_alumnos_sigae.csv"', response['Content-Disposition'])
        content = response.content.decode('utf-8')
        self.assertIn('Nombres,Apellidos,DNI,Area_Academica', content)
        self.assertIn('INGENIERIAS', content)


class PadronAlumnosTestCase(TestCase):
    """
    Prueba el listado, filtrado, edición y cambio de estado de alumnos en el padrón.
    """

    def setUp(self):
        self.secretaria = Usuario.objects.create_user(
            username="SECRE_PADRON",
            password="123",
            rol=Usuario.ROL_SECRETARIA
        )
        self.alumno1 = Usuario.objects.create_user(
            username="ALUMNO1",
            first_name="Carlos",
            last_name="Quispe",
            password="123",
            rol=Usuario.ROL_ALUMNO,
            dni="71112233",
            area_academica="INGENIERIAS",
            is_active=True
        )
        self.alumno2 = Usuario.objects.create_user(
            username="ALUMNO2",
            first_name="Diana",
            last_name="Mamani",
            password="123",
            rol=Usuario.ROL_ALUMNO,
            dni="72223344",
            area_academica="BIOMEDICAS",
            is_active=False
        )

    def test_listar_y_filtrar_alumnos(self):
        from django.urls import reverse
        self.client.login(username="SECRE_PADRON", password="123")

        # Listado completo
        response = self.client.get(reverse('listar_alumnos'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_alumnos'], 2)

        # Filtro por búsqueda DNI
        response_q = self.client.get(reverse('listar_alumnos') + '?q=71112233')
        self.assertEqual(response_q.status_code, 200)
        self.assertEqual(response_q.context['total_alumnos'], 1)

        # Filtro por área
        response_area = self.client.get(reverse('listar_alumnos') + '?area=BIOMEDICAS')
        self.assertEqual(response_area.status_code, 200)
        self.assertEqual(response_area.context['total_alumnos'], 1)

        # Filtro por estado activo
        response_act = self.client.get(reverse('listar_alumnos') + '?estado=activo')
        self.assertEqual(response_act.status_code, 200)
        self.assertEqual(response_act.context['total_alumnos'], 1)

    def test_editar_alumno(self):
        from django.urls import reverse
        self.client.login(username="SECRE_PADRON", password="123")

        response = self.client.post(
            reverse('editar_alumno', args=[self.alumno1.id]),
            {
                'nombres': 'Carlos Alberto',
                'apellidos': 'Quispe Ramos',
                'telefono': '999888777',
                'email': 'carlos.mod@test.com',
                'direccion': 'Av Floral 555',
                'area_academica': 'INGENIERIAS',
                'is_active': '1'
            }
        )
        self.assertEqual(response.status_code, 302)
        self.alumno1.refresh_from_db()
        self.assertEqual(self.alumno1.first_name, 'Carlos Alberto')
        self.assertEqual(self.alumno1.telefono, '999888777')
        self.assertEqual(self.alumno1.email, 'carlos.mod@test.com')

    def test_cambiar_estado_alumno(self):
        from django.urls import reverse
        self.client.login(username="SECRE_PADRON", password="123")

        self.assertTrue(self.alumno1.is_active)
        response = self.client.post(reverse('cambiar_estado_alumno', args=[self.alumno1.id]))
        self.assertEqual(response.status_code, 302)
        self.alumno1.refresh_from_db()
        self.assertFalse(self.alumno1.is_active)


class DashboardAlumnoMetricasTestCase(TestCase):
    """
    Prueba las tarjetas métricas del alumno (último simulacro con ranking y récord de asistencia).
    """

    def setUp(self):
        self.alumno = Usuario.objects.create_user(
            username="ALUMNO_METRICAS",
            first_name="Rodrigo",
            last_name="Perez",
            password="123",
            rol=Usuario.ROL_ALUMNO,
            area_academica="INGENIERIAS"
        )
        self.otro_alumno = Usuario.objects.create_user(
            username="ALUMNO_TOP",
            first_name="Mateo",
            last_name="Quispe",
            password="123",
            rol=Usuario.ROL_ALUMNO,
            area_academica="INGENIERIAS"
        )

    def test_dashboard_alumno_metricas(self):
        import datetime
        from django.urls import reverse
        from simulacros.models import Simulacro, ResultadoSimulacro
        from academico.models import AsistenciaQR, Ciclo, Matricula
        hoy = datetime.date.today()

        # Crear ciclo y matricula
        ciclo = Ciclo.objects.create(
            nombre="Ordinario 2026",
            fecha_inicio=hoy - datetime.timedelta(days=10),
            fecha_fin=hoy + datetime.timedelta(days=60),
            activo=True
        )
        Matricula.objects.create(
            alumno=self.alumno,
            ciclo=ciclo,
            codigo_matricula="EULER-1-1",
            activo=True
        )

        # Crear asistencias
        AsistenciaQR.objects.create(
            alumno=self.alumno,
            codigo_qr_escaneado="QR_ASIS_1",
            estado="PRESENTE"
        )

        # Crear simulacro con 2 resultados
        sim = Simulacro.objects.create(
            titulo="Simulacro General 1",
            fecha=hoy,
            area_academica="INGENIERIAS",
            puntaje_maximo=400.00,
            activo=True
        )
        ResultadoSimulacro.objects.create(
            alumno=self.otro_alumno,
            simulacro=sim,
            puntaje_total=350.00
        )
        ResultadoSimulacro.objects.create(
            alumno=self.alumno,
            simulacro=sim,
            puntaje_total=300.00
        )

        self.client.login(username="ALUMNO_METRICAS", password="123")
        response = self.client.get(reverse('dashboard_alumno'))
        self.assertEqual(response.status_code, 200)

        # Verificar datos del último simulacro
        ultimo_sim = response.context['ultimo_simulacro']
        self.assertIsNotNone(ultimo_sim)
        self.assertEqual(ultimo_sim['puntaje'], 300.00)
        self.assertEqual(ultimo_sim['puesto'], 2)  # El otro sacó 350, este alumno es puesto 2
        self.assertEqual(ultimo_sim['total_area'], 2)

        # Verificar datos de asistencia
        record = response.context['record_asistencia']
        self.assertEqual(record['total_sesiones'], 1)
        self.assertEqual(record['presentes'], 1)
        self.assertEqual(record['porcentaje'], 100.0)


class AdminDashboardTestCase(TestCase):
    """
    Prueba el enrutamiento y las métricas globales del Dashboard de Administrador (Director).
    """

    def setUp(self):
        self.admin = Usuario.objects.create_user(
            username="DIRECTOR_ADMIN",
            password="123",
            rol=Usuario.ROL_ADMIN,
            first_name="Director",
            last_name="General"
        )
        self.docente = Usuario.objects.create_user(
            username="DOCENTE_PAGO",
            password="123",
            rol=Usuario.ROL_DOCENTE,
            curso_asignado="Geometría",
            precio_hora=40.00
        )
        self.alumno = Usuario.objects.create_user(
            username="ALUMNO_PAGO",
            password="123",
            rol=Usuario.ROL_ALUMNO,
            area_academica="INGENIERIAS"
        )

    def test_login_redirect_admin(self):
        from django.urls import reverse
        response = self.client.post(
            reverse('iniciar_sesion'),
            {'username': 'DIRECTOR_ADMIN', 'password': '123'}
        )
        self.assertRedirects(response, reverse('dashboard_admin'))

    def test_dashboard_admin_metrics(self):
        import datetime
        from django.urls import reverse
        from academico.models import AsistenciaDocente, AsistenciaQR
        hoy = datetime.date.today()

        # Asistencia docente (3 horas x 40 S/ = 120 S/)
        AsistenciaDocente.objects.create(
            docente=self.docente,
            horas_dictadas=3.0,
            codigo_qr_escaneado="QR_DOC_ADMIN"
        )

        # Asistencia alumno hoy
        AsistenciaQR.objects.create(
            alumno=self.alumno,
            codigo_qr_escaneado="QR_ALU_ADMIN",
            estado="PRESENTE"
        )

        self.client.login(username="DIRECTOR_ADMIN", password="123")
        response = self.client.get(reverse('dashboard_admin'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_alumnos_activos'], 1)
        self.assertEqual(response.context['total_docentes_activos'], 1)
        self.assertEqual(response.context['asistencias_hoy_alumnos'], 1)
        self.assertEqual(response.context['porcentaje_asistencia_hoy'], 100.0)
        self.assertEqual(response.context['total_horas_dictadas_mes'], 3.0)
        self.assertEqual(response.context['total_planilla_mes'], 120.00)


class AdminDocentesManagementTestCase(TestCase):
    """
    Prueba la gestión integral de la plana docente por el Administrador.
    """

    def setUp(self):
        self.admin = Usuario.objects.create_user(
            username="ADMIN_PLANA",
            password="123",
            rol=Usuario.ROL_ADMIN
        )
        self.docente = Usuario.objects.create_user(
            username="DOC_INICIAL",
            first_name="Marco",
            last_name="Flores",
            password="123",
            rol=Usuario.ROL_DOCENTE,
            dni="75556677",
            curso_asignado="Aritmética",
            precio_hora=30.00,
            is_active=True
        )

    def test_listar_docentes(self):
        from django.urls import reverse
        self.client.login(username="ADMIN_PLANA", password="123")
        response = self.client.get(reverse('listar_docentes'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_docentes'], 1)
        self.assertContains(response, "Aritmética")
        self.assertContains(response, "Marco Flores")

    def test_editar_docente(self):
        from django.urls import reverse
        self.client.login(username="ADMIN_PLANA", password="123")
        response = self.client.post(
            reverse('editar_docente', args=[self.docente.id]),
            {
                'nombres': 'Marco Antonio',
                'apellidos': 'Flores Mamani',
                'telefono': '987654321',
                'email': 'marco.mod@test.com',
                'direccion': 'Jr Lima 123',
                'curso_asignado': 'Trigonometría',
                'precio_hora': '45.00',
                'is_active': '1'
            }
        )
        self.assertEqual(response.status_code, 302)
        self.docente.refresh_from_db()
        self.assertEqual(self.docente.first_name, 'Marco Antonio')
        self.assertEqual(self.docente.curso_asignado, 'Trigonometría')
        self.assertEqual(float(self.docente.precio_hora), 45.00)

    def test_cambiar_estado_docente(self):
        from django.urls import reverse
        self.client.login(username="ADMIN_PLANA", password="123")
        self.assertTrue(self.docente.is_active)

        response = self.client.post(reverse('cambiar_estado_docente', args=[self.docente.id]))
        self.assertEqual(response.status_code, 302)
        self.docente.refresh_from_db()
        self.assertFalse(self.docente.is_active)




