from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    class Rol(models.TextChoices):
        PACIENTE = 'paciente', 'Paciente'
        RECEPCIONISTA = 'recepcionista', 'Recepcionista'
        MEDICO = 'medico', 'Médico'
        ADMIN = 'admin', 'Administrador'

    rol = models.CharField(
        max_length=20,
        choices=Rol.choices,
        default=Rol.PACIENTE,
    )
    dni = models.CharField(max_length=10, unique=True)
    celular = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name = 'usuario'
        verbose_name_plural = 'usuarios'

    def __str__(self):
        return f'{self.get_full_name()} ({self.get_rol_display()})'
