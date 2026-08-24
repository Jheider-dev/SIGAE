"""
Modelos de base de datos para la aplicación 'autenticacion'.

Define el modelo de usuario personalizado del sistema SIGAE con soporte
para roles de usuario de la Academia Preuniversitaria Euler.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    """
    Modelo de usuario personalizado del sistema SIGAE.

    Extiende el modelo de usuario predeterminado de Django para incluir roles
    específicos (Alumno, Docente, Secretaría) y otros datos de contacto.
    """

    ROL_ADMIN = 'ADMIN'
    ROL_SECRETARIA = 'SECRETARIA'
    ROL_DOCENTE = 'DOCENTE'
    ROL_ALUMNO = 'ALUMNO'

    ROLES_CHOICES = [
        (ROL_ADMIN, 'Administrador / Director'),
        (ROL_SECRETARIA, 'Secretaría'),
        (ROL_DOCENTE, 'Docente'),
        (ROL_ALUMNO, 'Alumno'),
    ]

    rol = models.CharField(
        max_length=20,
        choices=ROLES_CHOICES,
        default=ROL_ALUMNO,
        help_text="Rol asignado al usuario dentro de la academia."
    )

    AREA_INGENIERIAS = 'INGENIERIAS'
    AREA_BIOMEDICAS = 'BIOMEDICAS'
    AREA_SOCIALES = 'SOCIALES'

    AREAS_CHOICES = [
        (AREA_INGENIERIAS, 'Ingenierías'),
        (AREA_BIOMEDICAS, 'Biomédicas'),
        (AREA_SOCIALES, 'Sociales'),
    ]

    area_academica = models.CharField(
        max_length=20,
        choices=AREAS_CHOICES,
        blank=True,
        null=True,
        help_text="Área académica obligatoria para Alumnos."
    )

    curso_asignado = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Curso principal asignado al docente."
    )

    precio_hora = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0.00,
        help_text="Precio por hora de dictado del docente."
    )

    ciclo = models.ForeignKey(
        'academico.Ciclo',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='usuarios',
        help_text="Ciclo académico al que pertenece el usuario (especialmente Docente)."
    )

    dni = models.CharField(
        max_length=8,
        unique=True,
        null=True,
        blank=True,
        help_text="Documento Nacional de Identidad (8 dígitos)."
    )

    telefono = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        help_text="Número telefónico o celular de contacto."
    )

    direccion = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Dirección domiciliaria del usuario."
    )

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def __str__(self):
        """
        Retorna la representación legible en cadena del usuario.

        Returns:
            str: Nombre completo o nombre de usuario si no está definido.
        """
        nombre_completo = self.get_full_name()
        return nombre_completo if nombre_completo else self.username

    def es_alumno(self):
        """
        Verifica si el usuario tiene el rol de Alumno.

        Returns:
            bool: True si es Alumno, False en caso contrario.
        """
        return self.rol == self.ROL_ALUMNO

    def es_docente(self):
        """
        Verifica si el usuario tiene el rol de Docente.

        Returns:
            bool: True si es Docente, False en caso contrario.
        """
        return self.rol == self.ROL_DOCENTE

    def es_secretaria(self):
        """
        Verifica si el usuario tiene el rol de Secretaría.

        Returns:
            bool: True si es Secretaría, False en caso contrario.
        """
        return self.rol == self.ROL_SECRETARIA

    def obtener_token_qr(self):
        """
        Retorna el token identificador único para el código QR de asistencia.

        Returns:
            str: Token de identificación único del alumno.
        """
        return f"SIGAE-ALUMNO-{self.id}"

