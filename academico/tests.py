from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import Ciclo, Matricula, Aula

Usuario = get_user_model()


class CicloGestionTestCase(TestCase):
    """
    Pruebas unitarias e de integración para la gestión de Ciclos
    y matrículas por parte del personal de Secretaría.
    """

    def setUp(self):
        # Crear secretaria
        self.secretaria = Usuario.objects.create_user(
            username="SEC001",
            password="123",
            rol=Usuario.ROL_SECRETARIA
        )
        # Crear docente
        self.docente = Usuario.objects.create_user(
            username="DOC001",
            password="123",
            rol=Usuario.ROL_DOCENTE
        )
        # Crear alumno
        self.alumno = Usuario.objects.create_user(
            username="ALU001",
            password="123",
            rol=Usuario.ROL_ALUMNO
        )

        # Crear ciclo inicial
        self.ciclo = Ciclo.objects.create(
            nombre="Ordinario 2026",
            fecha_inicio="2026-03-01",
            fecha_fin="2026-07-31",
            activo=True
        )

    def test_docente_no_puede_listar_ciclos(self):
        # El docente no debe tener acceso a la vista de gestión
        self.client.login(username="DOC001", password="123")
        response = self.client.get(reverse('listar_ciclos'))
        self.assertEqual(response.status_code, 302)

    def test_secretaria_puede_listar_y_crear_ciclos(self):
        # La secretaria sí debe acceder
        self.client.login(username="SEC001", password="123")
        response = self.client.get(reverse('listar_ciclos'))
        self.assertEqual(response.status_code, 200)

        # La secretaria crea un nuevo ciclo
        response_post = self.client.post(
            reverse('listar_ciclos'),
            {
                'nombre': 'Ciclo Intensivo Verano',
                'fecha_inicio': '2026-01-05',
                'fecha_fin': '2026-02-28',
                'descripcion': 'Exclusivo verano'
            }
        )
        self.assertEqual(response_post.status_code, 302)
        
        # Verificar creación
        self.assertTrue(Ciclo.objects.filter(nombre='Ciclo Intensivo Verano').exists())

    def test_secretaria_matricular_y_retirar_alumno(self):
        self.client.login(username="SEC001", password="123")
        
        # Agregar alumno al ciclo (Matricular)
        response_add = self.client.post(
            reverse('gestionar_alumnos_ciclo', args=[self.ciclo.id]),
            {
                'alumno_id': self.alumno.id,
                'accion': 'agregar'
            }
        )
        self.assertEqual(response_add.status_code, 302)
        self.assertTrue(Matricula.objects.filter(alumno=self.alumno, ciclo=self.ciclo).exists())

        # Retirar alumno del ciclo
        response_remove = self.client.post(
            reverse('gestionar_alumnos_ciclo', args=[self.ciclo.id]),
            {
                'alumno_id': self.alumno.id,
                'accion': 'eliminar'
            }
        )
        self.assertEqual(response_remove.status_code, 302)
        self.assertFalse(Matricula.objects.filter(alumno=self.alumno, ciclo=self.ciclo).exists())

    def test_secretaria_editar_ciclo(self):
        self.client.login(username="SEC001", password="123")

        response = self.client.post(
            reverse('editar_ciclo', args=[self.ciclo.id]),
            {
                'nombre': 'Ordinario 2026 Modificado',
                'fecha_inicio': '2026-03-15',
                'fecha_fin': '2026-08-15',
                'descripcion': 'Nueva descripción',
                'activo': '1'
            }
        )
        self.assertEqual(response.status_code, 302)
        self.ciclo.refresh_from_db()
        self.assertEqual(self.ciclo.nombre, 'Ordinario 2026 Modificado')
        self.assertEqual(str(self.ciclo.fecha_inicio), '2026-03-15')

    def test_secretaria_cambiar_estado_ciclo(self):
        self.client.login(username="SEC001", password="123")

        self.assertTrue(self.ciclo.activo)
        response = self.client.post(reverse('cambiar_estado_ciclo', args=[self.ciclo.id]))
        self.assertEqual(response.status_code, 302)
        self.ciclo.refresh_from_db()
        self.assertFalse(self.ciclo.activo)


class AsistenciaQRAreaRolTestCase(TestCase):
    """
    Prueba que la vista y respuesta de escaneo de Asistencia QR incluya
    el detalle de Rol y Área Académica / Curso.
    """

    def setUp(self):
        self.secretaria = Usuario.objects.create_user(
            username="SEC_ASIS",
            password="123",
            rol=Usuario.ROL_SECRETARIA
        )
        self.alumno = Usuario.objects.create_user(
            username="ALU_ING",
            first_name="Marco",
            last_name="Tapia",
            password="123",
            rol=Usuario.ROL_ALUMNO,
            area_academica="INGENIERIAS"
        )
        self.docente = Usuario.objects.create_user(
            username="DOC_MAT",
            first_name="Profesor",
            last_name="Euler",
            password="123",
            rol=Usuario.ROL_DOCENTE,
            curso_asignado="Álgebra Superior"
        )

    def test_asistencia_qr_contexto_inicial_contiene_rol_area(self):
        from .models import AsistenciaQR, AsistenciaDocente
        AsistenciaQR.objects.create(
            alumno=self.alumno,
            codigo_qr_escaneado="TOKEN123",
            estado="PRESENTE"
        )
        AsistenciaDocente.objects.create(
            docente=self.docente,
            horas_dictadas=2.0,
            codigo_qr_escaneado="TOKENDOC123"
        )

        self.client.login(username="SEC_ASIS", password="123")
        response = self.client.get(reverse('control_asistencia'))
        self.assertEqual(response.status_code, 200)

        asistencias = response.context['asistencias_list']
        self.assertEqual(len(asistencias), 2)
        roles_areas = [a['rol_area'] for a in asistencias]
        self.assertIn('Alumno - Ingenierías', roles_areas)
        self.assertIn('Docente - Álgebra Superior', roles_areas)


class PagosPensionesTestCase(TestCase):
    """
    Pruebas unitarias para el módulo de pagos, cuotas y pensiones.
    """

    def setUp(self):
        self.admin = Usuario.objects.create_user(
            username="ADMIN_PAGOS",
            password="123",
            rol=Usuario.ROL_ADMIN
        )
        self.secretaria = Usuario.objects.create_user(
            username="SEC_PAGOS",
            password="123",
            rol=Usuario.ROL_SECRETARIA
        )
        self.alumno = Usuario.objects.create_user(
            username="ALU_PAGOS",
            first_name="Carlos",
            last_name="Quispe",
            dni="78945612",
            password="123",
            rol=Usuario.ROL_ALUMNO,
            area_academica="INGENIERIAS"
        )
        self.ciclo = Ciclo.objects.create(
            nombre="Ordinario 2026",
            fecha_inicio="2026-03-01",
            fecha_fin="2026-07-31",
            activo=True
        )

    def test_secretaria_registrar_pago(self):
        from .models import Pago
        self.client.login(username="SEC_PAGOS", password="123")

        response = self.client.post(
            reverse('registrar_pago_alumno', args=[self.alumno.id]),
            {
                'alumno_id': self.alumno.id,
                'concepto': Pago.CONCEPTO_MATRICULA,
                'monto': '200.00',
                'metodo_pago': Pago.METODO_EFECTIVO,
                'estado': Pago.ESTADO_PAGADO,
                'fecha_pago': '2026-03-05',
                'numero_operacion': 'REC-001'
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Pago.objects.filter(alumno=self.alumno, concepto=Pago.CONCEPTO_MATRICULA, monto=200.00).exists())

    def test_control_pagos_view(self):
        from .models import Pago
        Pago.objects.create(
            alumno=self.alumno,
            ciclo=self.ciclo,
            concepto=Pago.CONCEPTO_MATRICULA,
            monto=150.00,
            estado=Pago.ESTADO_PAGADO,
            fecha_pago="2026-03-01",
            registrado_por=self.secretaria
        )
        self.client.login(username="ADMIN_PAGOS", password="123")
        response = self.client.get(reverse('control_pagos'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "150")

    def test_historial_pagos_alumno_view(self):
        from .models import Pago
        Pago.objects.create(
            alumno=self.alumno,
            ciclo=self.ciclo,
            concepto=Pago.CONCEPTO_PENSION_1,
            monto=250.00,
            estado=Pago.ESTADO_PAGADO,
            fecha_pago="2026-03-10",
            registrado_por=self.secretaria
        )
        self.client.login(username="SEC_PAGOS", password="123")
        response = self.client.get(reverse('historial_pagos_alumno', args=[self.alumno.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Carlos Quispe")
        self.assertContains(response, "250")


class ExportacionesCSVTestCase(TestCase):
    """
    Pruebas para las descargas y exportaciones en formato CSV compatible con Excel.
    """

    def setUp(self):
        self.admin = Usuario.objects.create_user(
            username="ADMIN_EXP",
            password="123",
            rol=Usuario.ROL_ADMIN
        )
        self.docente = Usuario.objects.create_user(
            username="DOC_EXP",
            first_name="Profesor",
            last_name="Química",
            dni="71234567",
            precio_hora=40.0,
            password="123",
            rol=Usuario.ROL_DOCENTE,
            curso_asignado="Química"
        )
        self.alumno = Usuario.objects.create_user(
            username="ALU_EXP",
            first_name="Diana",
            last_name="Morales",
            dni="74561230",
            password="123",
            rol=Usuario.ROL_ALUMNO,
            area_academica="BIOMEDICAS"
        )

    def test_exportar_alumnos_csv(self):
        self.client.login(username="ADMIN_EXP", password="123")
        response = self.client.get(reverse('exportar_alumnos_csv'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        content = response.content.decode('utf-8-sig')
        self.assertIn('Diana', content)
        self.assertIn('74561230', content)

    def test_exportar_asistencias_csv(self):
        from .models import AsistenciaQR
        AsistenciaQR.objects.create(
            alumno=self.alumno,
            codigo_qr_escaneado="TOKEN_TEST",
            estado="PRESENTE"
        )
        self.client.login(username="ADMIN_EXP", password="123")
        response = self.client.get(reverse('exportar_asistencias_csv'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8-sig')
        self.assertIn('Diana Morales', content)

    def test_exportar_liquidacion_docentes_csv(self):
        import datetime
        from .models import AsistenciaDocente
        hoy = datetime.date.today()
        AsistenciaDocente.objects.create(
            docente=self.docente,
            horas_dictadas=3.0,
            codigo_qr_escaneado="DOC_TOKEN"
        )
        self.client.login(username="ADMIN_EXP", password="123")
        response = self.client.get(f"{reverse('exportar_liquidacion_docentes_csv')}?mes={hoy.month}&anio={hoy.year}")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8-sig')
        self.assertIn('Profesor Química', content)
        self.assertIn('120.00', content)  # 3 horas * 40 S/.


class DocenteHistorialTestCase(TestCase):
    """
    Prueba de la vista de mis asistencias del docente.
    """

    def setUp(self):
        self.docente = Usuario.objects.create_user(
            username="DOC_HIST",
            first_name="Mario",
            last_name="Vargas",
            precio_hora=35.0,
            password="123",
            rol=Usuario.ROL_DOCENTE,
            curso_asignado="Literatura"
        )

    def test_mis_asistencias_docente(self):
        from .models import AsistenciaDocente
        AsistenciaDocente.objects.create(
            docente=self.docente,
            horas_dictadas=2.0,
            codigo_qr_escaneado="TOKENDOC"
        )
        self.client.login(username="DOC_HIST", password="123")
        response = self.client.get(reverse('mis_asistencias_docente'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Literatura")
        self.assertContains(response, "70")  # 2 hrs * 35 S/.



class SimulacroRevisionTestCase(TestCase):
    """
    Pruebas para la revisión de simulacros por parte del alumno y exportación de ranking.
    """

    def setUp(self):
        self.alumno = Usuario.objects.create_user(
            username="ALU_REV",
            first_name="Sonia",
            last_name="Apaza",
            dni="70123456",
            password="123",
            rol=Usuario.ROL_ALUMNO,
            area_academica="SOCIALES"
        )
        from simulacros.models import Simulacro, Pregunta, ResultadoSimulacro, DetalleRespuesta
        self.simulacro = Simulacro.objects.create(
            titulo="Simulacro Tipo Examen Sociales",
            fecha="2026-03-20",
            area_academica="SOCIALES",
            puntaje_maximo=400.0,
            activo=True
        )
        self.pregunta = Pregunta.objects.create(
            simulacro=self.simulacro,
            numero_pregunta=1,
            enunciado="¿Capital del Perú?",
            alternativa_a="Lima",
            alternativa_b="Cusco",
            alternativa_c="Puno",
            alternativa_d="Arequipa",
            alternativa_correcta="A",
            puntaje_correcta=4.0,
            puntaje_incorrecta=-1.0,
            puntaje_omitida=0.0
        )
        self.resultado = ResultadoSimulacro.objects.create(
            alumno=self.alumno,
            simulacro=self.simulacro,
            puntaje_total=4.0,
            respuestas_correctas=1,
            respuestas_incorrectas=0,
            respuestas_omitidas=0
        )
        DetalleRespuesta.objects.create(
            resultado=self.resultado,
            pregunta=self.pregunta,
            alternativa_marcada='A',
            puntaje_obtenido=4.0
        )

    def test_ver_revision_simulacro(self):
        self.client.login(username="ALU_REV", password="123")
        response = self.client.get(reverse('ver_revision_simulacro', args=[self.simulacro.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "¿Capital del Perú?")
        self.assertContains(response, "Respuesta Correcta")

    def test_exportar_ranking_simulacro_csv(self):
        admin = Usuario.objects.create_user(username="ADMIN_SIM", password="123", rol=Usuario.ROL_ADMIN)
        self.client.login(username="ADMIN_SIM", password="123")
        response = self.client.get(reverse('exportar_ranking_simulacro_csv', args=[self.simulacro.id]))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8-sig')
        self.assertIn('Sonia', content)
        self.assertIn('70123456', content)


