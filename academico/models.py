"""
Modelos de base de datos para la aplicación 'academico'.

Define las estructuras de ciclo de preparación, aulas, matrículas de alumnos
y el registro de asistencia mediante código QR para el sistema SIGAE.
"""

from django.conf import settings
from django.db import models


class Ciclo(models.Model):
    """
    Representa un periodo académico o ciclo de preparación en la academia.

    Ejemplos: Ciclo Ordinario, Ciclo Intensivo, Ciclo Semestral.
    """

    nombre = models.CharField(
        max_length=100,
        help_text="Nombre descriptivo del ciclo académico (ej. Ordinario 2026-I)."
    )
    fecha_inicio = models.DateField(
        help_text="Fecha de inicio oficial del ciclo."
    )
    fecha_fin = models.DateField(
        help_text="Fecha de finalización programada del ciclo."
    )
    activo = models.BooleanField(
        default=True,
        help_text="Indica si el ciclo está activo actualmente para matrículas o dictado."
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        help_text="Detalles adicionales sobre el ciclo."
    )

    class Meta:
        verbose_name = "Ciclo"
        verbose_name_plural = "Ciclos"

    def __str__(self):
        """
        Retorna la representación en texto del ciclo académico.

        Returns:
            str: Nombre del ciclo.
        """
        return self.nombre


class Aula(models.Model):
    """
    Representa un aula física o salón asignado a los grupos de estudiantes.
    """

    nombre = models.CharField(
        max_length=50,
        unique=True,
        help_text="Identificador único del aula (ej. Aula 101, Salón B)."
    )
    capacidad = models.PositiveIntegerField(
        default=40,
        help_text="Capacidad máxima de alumnos permitidos en el aula."
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        help_text="Descripción del equipamiento o ubicación del aula."
    )

    class Meta:
        verbose_name = "Aula"
        verbose_name_plural = "Aulas"

    def __str__(self):
        """
        Retorna la representación en texto del aula.

        Returns:
            str: Nombre del aula.
        """
        return self.nombre


class Matricula(models.Model):
    """
    Representa el registro de inscripción de un Alumno en un Ciclo específico,
    con opción de asignarle un Aula física de clases.
    """

    alumno = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="matriculas",
        limit_choices_to={'rol': 'ALUMNO'},
        help_text="Alumno que realiza la matrícula."
    )
    ciclo = models.ForeignKey(
        Ciclo,
        on_delete=models.PROTECT,
        related_name="matriculas",
        help_text="Ciclo de preparación al que se inscribe el alumno."
    )
    aula = models.ForeignKey(
        Aula,
        on_delete=models.SET_NULL,
        related_name="matriculas",
        blank=True,
        null=True,
        help_text="Aula física asignada al alumno para sus clases presenciales."
    )
    codigo_matricula = models.CharField(
        max_length=20,
        unique=True,
        help_text="Código único de matrícula generado para el alumno."
    )
    fecha_matricula = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha y hora exactas en que se registró la matrícula."
    )
    activo = models.BooleanField(
        default=True,
        help_text="Indica si la matrícula se encuentra vigente."
    )

    class Meta:
        verbose_name = "Matrícula"
        verbose_name_plural = "Matrículas"
        unique_together = ('alumno', 'ciclo')

    def __str__(self):
        """
        Retorna la representación en texto de la matrícula.

        Returns:
            str: Detalle resumido de la matrícula.
        """
        return f"{self.codigo_matricula} - {self.alumno} ({self.ciclo})"


class AsistenciaQR(models.Model):
    """
    Registra el control de asistencia diaria de un Alumno a través del escaneo
    de códigos QR en el ingreso de la academia o salones de clase.
    """

    ESTADO_PRESENTE = 'PRESENTE'
    ESTADO_TARDE = 'TARDE'
    ESTADO_FALTA = 'FALTA'

    ESTADOS_CHOICES = [
        (ESTADO_PRESENTE, 'Presente'),
        (ESTADO_TARDE, 'Tarde'),
        (ESTADO_FALTA, 'Falta'),
    ]

    alumno = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="asistencias_qr",
        limit_choices_to={'rol': 'ALUMNO'},
        help_text="Alumno asociado al registro de asistencia."
    )
    fecha = models.DateField(
        auto_now_add=True,
        help_text="Fecha del registro de asistencia."
    )
    hora_acceso = models.TimeField(
        auto_now_add=True,
        help_text="Hora exacta del escaneo y acceso."
    )
    codigo_qr_escaneado = models.CharField(
        max_length=255,
        help_text="Identificador único o token desencriptado del código QR escaneado."
    )
    estado = models.CharField(
        max_length=15,
        choices=ESTADOS_CHOICES,
        default=ESTADO_PRESENTE,
        help_text="Estado de la asistencia calculada al momento del ingreso."
    )

    class Meta:
        verbose_name = "Asistencia QR"
        verbose_name_plural = "Asistencias QR"

    def __str__(self):
        """
        Retorna la representación legible de la asistencia.

        Returns:
            str: Detalle de asistencia.
        """
        return f"{self.alumno} - {self.fecha} ({self.estado})"


class AsistenciaDocente(models.Model):
    """
    Registra el control de asistencia diaria de un Docente, con las horas dictadas
    validadas o modificadas por Secretaría.
    """

    docente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="asistencias_docente",
        limit_choices_to={'rol': 'DOCENTE'},
        help_text="Docente asociado al registro de asistencia."
    )
    fecha = models.DateField(
        auto_now_add=True,
        help_text="Fecha del registro de asistencia."
    )
    hora_acceso = models.TimeField(
        auto_now_add=True,
        help_text="Hora exacta del escaneo."
    )
    horas_dictadas = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=1.50,
        help_text="Horas de dictado validadas por Secretaría."
    )
    codigo_qr_escaneado = models.CharField(
        max_length=255,
        help_text="Token QR dinámico validado."
    )

    class Meta:
        verbose_name = "Asistencia Docente"
        verbose_name_plural = "Asistencias Docente"

    def __str__(self):
        return f"{self.docente} - {self.fecha} ({self.horas_dictadas} hrs)"


class Pago(models.Model):
    """
    Registra los cobros de matrículas, cuotas y pensiones asociados a cada alumno.
    """

    CONCEPTO_MATRICULA = 'MATRICULA'
    CONCEPTO_PENSION_1 = 'PENSION_1'
    CONCEPTO_PENSION_2 = 'PENSION_2'
    CONCEPTO_PENSION_3 = 'PENSION_3'
    CONCEPTO_SIMULACRO = 'SIMULACRO'
    CONCEPTO_MATERIAL = 'MATERIAL'
    CONCEPTO_OTRO = 'OTRO'

    CONCEPTOS_CHOICES = [
        (CONCEPTO_MATRICULA, 'Matrícula'),
        (CONCEPTO_PENSION_1, 'Pensión 1 (Mes 1)'),
        (CONCEPTO_PENSION_2, 'Pensión 2 (Mes 2)'),
        (CONCEPTO_PENSION_3, 'Pensión 3 (Mes 3)'),
        (CONCEPTO_SIMULACRO, 'Derecho de Simulacro'),
        (CONCEPTO_MATERIAL, 'Guías y Material'),
        (CONCEPTO_OTRO, 'Otro Concepto'),
    ]

    ESTADO_PAGADO = 'PAGADO'
    ESTADO_PENDIENTE = 'PENDIENTE'
    ESTADO_ANULADO = 'ANULADO'

    ESTADOS_CHOICES = [
        (ESTADO_PAGADO, 'Pagado / Al día'),
        (ESTADO_PENDIENTE, 'Pendiente / Deudor'),
        (ESTADO_ANULADO, 'Anulado'),
    ]

    METODO_EFECTIVO = 'EFECTIVO'
    METODO_YAPE_PLIN = 'YAPE_PLIN'
    METODO_TRANSFERENCIA = 'TRANSFERENCIA'
    METODO_TARJETA = 'TARJETA'

    METODOS_CHOICES = [
        (METODO_EFECTIVO, 'Efectivo'),
        (METODO_YAPE_PLIN, 'Yape / Plin'),
        (METODO_TRANSFERENCIA, 'Transferencia Bancaria'),
        (METODO_TARJETA, 'Tarjeta'),
    ]

    alumno = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pagos",
        limit_choices_to={'rol': 'ALUMNO'},
        help_text="Alumno asociado al pago o pensión."
    )
    ciclo = models.ForeignKey(
        Ciclo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pagos",
        help_text="Ciclo académico correspondiente."
    )
    concepto = models.CharField(
        max_length=30,
        choices=CONCEPTOS_CHOICES,
        default=CONCEPTO_MATRICULA,
        help_text="Concepto del cobro realizado."
    )
    monto = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text="Monto abonado en soles (S/.)."
    )
    estado = models.CharField(
        max_length=15,
        choices=ESTADOS_CHOICES,
        default=ESTADO_PAGADO,
        help_text="Estado del pago."
    )
    metodo_pago = models.CharField(
        max_length=20,
        choices=METODOS_CHOICES,
        default=METODO_EFECTIVO,
        help_text="Forma de pago utilizada."
    )
    numero_operacion = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Número de comprobante, ticket u operación bancaria."
    )
    fecha_pago = models.DateField(
        help_text="Fecha en que se efectuó el pago."
    )
    fecha_registro = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha y hora de registro en el sistema."
    )
    observaciones = models.TextField(
        blank=True,
        null=True,
        help_text="Observaciones o notas adicionales."
    )
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pagos_registrados",
        help_text="Usuario de Secretaría o Administrador que registró el pago."
    )

    class Meta:
        verbose_name = "Pago y Pensión"
        verbose_name_plural = "Pagos y Pensiones"
        ordering = ['-fecha_pago', '-id']

    def __str__(self):
        return f"{self.alumno} - {self.get_concepto_display()} (S/. {self.monto})"

