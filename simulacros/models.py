"""
Modelos de base de datos para la aplicación 'simulacros'.

Define las estructuras para exámenes/simulacros, el banco de preguntas,
las respuestas de los postulantes y el cálculo de puntajes académicos
para la Academia Preuniversitaria Euler.
"""

from django.conf import settings
from django.db import models


class Simulacro(models.Model):
    """
    Representa un examen tipo simulacro programado por la academia.
    """

    AREA_INGENIERIAS = 'INGENIERIAS'
    AREA_BIOMEDICAS = 'BIOMEDICAS'
    AREA_SOCIALES = 'SOCIALES'

    AREAS_CHOICES = [
        (AREA_INGENIERIAS, 'Ingenierías'),
        (AREA_BIOMEDICAS, 'Biomédicas'),
        (AREA_SOCIALES, 'Sociales'),
    ]

    titulo = models.CharField(
        max_length=150,
        help_text="Título descriptivo del simulacro (ej. Primer Simulacro de Admisión)."
    )
    fecha = models.DateField(
        help_text="Fecha programada en que se rinde el simulacro."
    )
    area_academica = models.CharField(
        max_length=20,
        choices=AREAS_CHOICES,
        default=AREA_INGENIERIAS,
        help_text="Área académica asociada al simulacro."
    )
    puntaje_maximo = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=400.00,
        help_text="Puntaje total máximo alcanzable en la prueba."
    )
    activo = models.BooleanField(
        default=True,
        help_text="Indica si el simulacro está activo y visible en el sistema."
    )
    descripcion = models.TextField(
        blank=True,
        null=True,
        help_text="Notas o instrucciones adicionales del examen."
    )
    docente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="simulacros_creados",
        limit_choices_to={'rol': 'DOCENTE'},
        help_text="Docente que programó o elaboró el simulacro."
    )

    class Meta:
        verbose_name = "Simulacro"
        verbose_name_plural = "Simulacros"

    def __str__(self):
        """
        Retorna la representación legible en cadena del simulacro.

        Returns:
            str: Título del simulacro.
        """
        return self.titulo


class Pregunta(models.Model):
    """
    Representa una pregunta de opción múltiple vinculada a un simulacro.
    """

    ALTERNATIVAS_CHOICES = [
        ('A', 'Alternativa A'),
        ('B', 'Alternativa B'),
        ('C', 'Alternativa C'),
        ('D', 'Alternativa D'),
        ('E', 'Alternativa E'),
    ]

    simulacro = models.ForeignKey(
        Simulacro,
        on_delete=models.CASCADE,
        related_name="preguntas",
        help_text="Simulacro al que pertenece esta pregunta."
    )
    numero_pregunta = models.PositiveIntegerField(
        help_text="Número correlativo de la pregunta dentro del examen."
    )
    enunciado = models.TextField(
        help_text="Enunciado de la pregunta en texto plano."
    )
    alternativa_a = models.TextField(
        help_text="Opción A de la pregunta."
    )
    alternativa_b = models.TextField(
        help_text="Opción B de la pregunta."
    )
    alternativa_c = models.TextField(
        help_text="Opción C de la pregunta."
    )
    alternativa_d = models.TextField(
        help_text="Opción D de la pregunta."
    )
    alternativa_e = models.TextField(
        blank=True,
        null=True,
        help_text="Opción E de la pregunta (opcional para exámenes de 4 alternativas)."
    )
    alternativa_correcta = models.CharField(
        max_length=1,
        choices=ALTERNATIVAS_CHOICES,
        help_text="Alternativa válida que se considera respuesta correcta."
    )
    puntaje_correcta = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=4.00,
        help_text="Puntaje obtenido por contestar correctamente."
    )
    puntaje_incorrecta = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=-1.00,
        help_text="Puntaje (penalización) obtenido por contestar incorrectamente."
    )
    puntaje_omitida = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="Puntaje obtenido por omitir la pregunta."
    )

    class Meta:
        verbose_name = "Pregunta"
        verbose_name_plural = "Preguntas"
        unique_together = ('simulacro', 'numero_pregunta')

    def __str__(self):
        """
        Retorna la representación legible de la pregunta.

        Returns:
            str: Identificador de la pregunta.
        """
        return f"Pregunta {self.numero_pregunta} - {self.simulacro}"


class ResultadoSimulacro(models.Model):
    """
    Consolida las calificaciones obtenidas por un alumno en un simulacro.
    """

    alumno = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="resultados_simulacros",
        limit_choices_to={'rol': 'ALUMNO'},
        help_text="Alumno que rindió la evaluación."
    )
    simulacro = models.ForeignKey(
        Simulacro,
        on_delete=models.CASCADE,
        related_name="resultados",
        help_text="Simulacro evaluado."
    )
    puntaje_total = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0.00,
        help_text="Puntaje total final acumulado."
    )
    respuestas_correctas = models.PositiveIntegerField(
        default=0,
        help_text="Cantidad de respuestas correctas."
    )
    respuestas_incorrectas = models.PositiveIntegerField(
        default=0,
        help_text="Cantidad de respuestas incorrectas."
    )
    respuestas_omitidas = models.PositiveIntegerField(
        default=0,
        help_text="Cantidad de preguntas no contestadas u omitidas."
    )
    fecha_evaluacion = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha y hora de registro de la prueba."
    )

    class Meta:
        verbose_name = "Resultado de Simulacro"
        verbose_name_plural = "Resultados de Simulacros"
        unique_together = ('alumno', 'simulacro')

    def __str__(self):
        """
        Retorna la representación legible del resultado.

        Returns:
            str: Resumen del resultado.
        """
        return f"{self.alumno} - {self.simulacro} (Nota: {self.puntaje_total})"

    def calcular_y_actualizar_totales(self):
        """
        Calcula y actualiza los campos de puntaje total, correctas, incorrectas
        y omitidas basándose en los registros hijos de DetalleRespuesta.
        """
        detalles = self.detalles.all()
        total_puntos = 0.00
        correctas = 0
        incorrectas = 0
        omitidas = 0

        for det in detalles:
            total_puntos += float(det.puntaje_obtenido)
            if det.alternativa_marcada == 'O':
                omitidas += 1
            elif det.alternativa_marcada == det.pregunta.alternativa_correcta:
                correctas += 1
            else:
                incorrectas += 1

        self.puntaje_total = total_puntos
        self.respuestas_correctas = correctas
        self.respuestas_incorrectas = incorrectas
        self.respuestas_omitidas = omitidas
        self.save()


class DetalleRespuesta(models.Model):
    """
    Almacena la alternativa elegida por el alumno para una pregunta específica
    y calcula el puntaje individual de dicha respuesta.
    """

    MARCADAS_CHOICES = [
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D'),
        ('E', 'E'),
        ('O', 'Omitida'),
    ]

    resultado = models.ForeignKey(
        ResultadoSimulacro,
        on_delete=models.CASCADE,
        related_name="detalles",
        help_text="Encabezado del resultado al que pertenece este detalle."
    )
    pregunta = models.ForeignKey(
        Pregunta,
        on_delete=models.CASCADE,
        help_text="Pregunta que se está respondiendo."
    )
    alternativa_marcada = models.CharField(
        max_length=1,
        choices=MARCADAS_CHOICES,
        default='O',
        help_text="Alternativa seleccionada por el estudiante."
    )
    puntaje_obtenido = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text="Puntaje calculado obtenido para esta pregunta."
    )

    class Meta:
        verbose_name = "Detalle de Respuesta"
        verbose_name_plural = "Detalles de Respuestas"
        unique_together = ('resultado', 'pregunta')

    def __str__(self):
        """
        Retorna la representación legible del detalle de respuesta.

        Returns:
            str: Identificación de respuesta del estudiante.
        """
        return f"{self.resultado.alumno.username} - Pregunta {self.pregunta.numero_pregunta} ({self.alternativa_marcada})"

    def save(self, *args, **kwargs):
        """
        Sobrescribe el método save para calcular automáticamente el puntaje
        obtenido basado en la alternativa marcada y las ponderaciones de la pregunta.
        """
        if self.alternativa_marcada == 'O':
            self.puntaje_obtenido = self.pregunta.puntaje_omitida
        elif self.alternativa_marcada == self.pregunta.alternativa_correcta:
            self.puntaje_obtenido = self.pregunta.puntaje_correcta
        else:
            self.puntaje_obtenido = self.pregunta.puntaje_incorrecta

        super().save(*args, **kwargs)
        # Actualiza el acumulado del resultado padre
        self.resultado.calcular_y_actualizar_totales()
