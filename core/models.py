from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta


class Especialidad(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    activa = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'especialidades'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Medico(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='perfil_medico',
    )
    matricula = models.CharField(max_length=20, unique=True)
    especialidades = models.ManyToManyField(
        Especialidad,
        related_name='medicos',
    )

    class Meta:
        verbose_name_plural = 'médicos'
        ordering = ['usuario__last_name', 'usuario__first_name']

    def __str__(self):
        return f'Dr/a. {self.usuario.get_full_name()} - Mat. {self.matricula}'


class Paciente(models.Model):
    class Estado(models.TextChoices):
        ACTIVO = 'activo', 'Activo'
        BLOQUEADO = 'bloqueado', 'Bloqueado'

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='perfil_paciente',
    )
    estado = models.CharField(
        max_length=10,
        choices=Estado.choices,
        default=Estado.ACTIVO,
    )

    class Meta:
        ordering = ['usuario__last_name', 'usuario__first_name']

    def __str__(self):
        return f'{self.usuario.get_full_name()} (DNI: {self.usuario.dni})'

    @property
    def esta_bloqueado(self):
        return self.estado == self.Estado.BLOQUEADO

    def contar_noshows_recientes(self):
        """Cuenta no-shows en los últimos 60 días (RN-04)."""
        desde = timezone.now() - timedelta(days=60)
        return self.turnos.filter(
            estado=Turno.Estado.NO_SHOW,
            fecha_hora__gte=desde,
        ).count()

    def verificar_bloqueo(self):
        """Bloquea al paciente si acumuló 3+ no-shows en 60 días (RN-04)."""
        if self.contar_noshows_recientes() >= 3:
            self.estado = self.Estado.BLOQUEADO
            self.save(update_fields=['estado'])
            return True
        return False


class FamiliarPaciente(models.Model):
    class Parentesco(models.TextChoices):
        HIJO = 'hijo', 'Hijo/a'
        CONYUGE = 'conyuge', 'Cónyuge'
        PADRE = 'padre', 'Padre/Madre'

    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name='familiares',
    )
    nombre = models.CharField(max_length=150)
    dni = models.CharField(max_length=10)
    parentesco = models.CharField(
        max_length=10,
        choices=Parentesco.choices,
    )

    class Meta:
        verbose_name = 'familiar del paciente'
        verbose_name_plural = 'familiares del paciente'
        unique_together = ['paciente', 'dni']

    def __str__(self):
        return f'{self.nombre} ({self.get_parentesco_display()} de {self.paciente})'


class DisponibilidadMedica(models.Model):
    class DiaSemana(models.IntegerChoices):
        LUNES = 0, 'Lunes'
        MARTES = 1, 'Martes'
        MIERCOLES = 2, 'Miércoles'
        JUEVES = 3, 'Jueves'
        VIERNES = 4, 'Viernes'
        SABADO = 5, 'Sábado'

    medico = models.ForeignKey(
        Medico,
        on_delete=models.CASCADE,
        related_name='disponibilidades',
    )
    dia_semana = models.IntegerField(choices=DiaSemana.choices)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    duracion_turno = models.PositiveIntegerField(
        default=30,
        help_text='Duración de cada turno en minutos',
    )

    class Meta:
        verbose_name = 'disponibilidad médica'
        verbose_name_plural = 'disponibilidades médicas'
        unique_together = ['medico', 'dia_semana', 'hora_inicio']
        ordering = ['dia_semana', 'hora_inicio']

    def clean(self):
        if self.hora_inicio and self.hora_fin and self.hora_inicio >= self.hora_fin:
            raise ValidationError('La hora de inicio debe ser anterior a la hora de fin.')

    def __str__(self):
        return (
            f'{self.medico} - {self.get_dia_semana_display()} '
            f'{self.hora_inicio:%H:%M} a {self.hora_fin:%H:%M}'
        )


class BloqueoHorario(models.Model):
    medico = models.ForeignKey(
        Medico,
        on_delete=models.CASCADE,
        related_name='bloqueos',
    )
    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField()
    motivo = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = 'bloqueo de horario'
        verbose_name_plural = 'bloqueos de horario'
        ordering = ['fecha_inicio']

    def clean(self):
        if self.fecha_inicio and self.fecha_fin and self.fecha_inicio >= self.fecha_fin:
            raise ValidationError('La fecha de inicio debe ser anterior a la fecha de fin.')

    def __str__(self):
        return f'{self.medico} bloqueado {self.fecha_inicio:%d/%m/%Y} - {self.fecha_fin:%d/%m/%Y}'


class Turno(models.Model):
    class Estado(models.TextChoices):
        RESERVADO = 'reservado', 'Reservado'
        CONFIRMADO = 'confirmado', 'Confirmado'
        CANCELADO = 'cancelado', 'Cancelado'
        ATENDIDO = 'atendido', 'Atendido'
        NO_SHOW = 'no_show', 'No Show'

    class Canal(models.TextChoices):
        ONLINE = 'online', 'Online'
        TELEFONO = 'telefono', 'Teléfono'
        PRESENCIAL = 'presencial', 'Presencial'

    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name='turnos',
    )
    medico = models.ForeignKey(
        Medico,
        on_delete=models.CASCADE,
        related_name='turnos',
    )
    especialidad = models.ForeignKey(
        Especialidad,
        on_delete=models.PROTECT,
        related_name='turnos',
    )
    fecha_hora = models.DateTimeField()
    duracion = models.PositiveIntegerField(
        default=30,
        help_text='Duración en minutos',
    )
    estado = models.CharField(
        max_length=15,
        choices=Estado.choices,
        default=Estado.RESERVADO,
    )
    canal = models.CharField(
        max_length=15,
        choices=Canal.choices,
        default=Canal.ONLINE,
    )
    familiar = models.ForeignKey(
        FamiliarPaciente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='turnos',
    )
    hora_checkin = models.DateTimeField(null=True, blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='turnos_creados',
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['fecha_hora']
        indexes = [
            models.Index(fields=['medico', 'fecha_hora']),
            models.Index(fields=['paciente', 'fecha_hora']),
            models.Index(fields=['estado']),
        ]

    def __str__(self):
        return (
            f'Turno {self.id} - {self.paciente} con {self.medico} '
            f'el {self.fecha_hora:%d/%m/%Y %H:%M}'
        )

    @property
    def fecha_hora_fin(self):
        return self.fecha_hora + timedelta(minutes=self.duracion)

    @property
    def puede_cancelar(self):
        """RN-03: Cancelación con al menos 2 horas de anticipación."""
        return timezone.now() <= self.fecha_hora - timedelta(hours=2)

    @property
    def es_futuro(self):
        return self.fecha_hora > timezone.now()


class Notificacion(models.Model):
    class Tipo(models.TextChoices):
        RECORDATORIO = 'recordatorio', 'Recordatorio'
        CONFIRMACION = 'confirmacion', 'Confirmación'
        CANCELACION = 'cancelacion', 'Cancelación'
        NO_SHOW = 'no_show', 'No Show'

    class CanalEnvio(models.TextChoices):
        EMAIL = 'email', 'Email'
        SMS = 'sms', 'SMS'
        WHATSAPP = 'whatsapp', 'WhatsApp'

    class EstadoEnvio(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        ENVIADA = 'enviada', 'Enviada'
        FALLIDA = 'fallida', 'Fallida'

    turno = models.ForeignKey(
        Turno,
        on_delete=models.CASCADE,
        related_name='notificaciones',
    )
    destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notificaciones',
    )
    tipo = models.CharField(max_length=15, choices=Tipo.choices)
    canal_envio = models.CharField(
        max_length=10,
        choices=CanalEnvio.choices,
        default=CanalEnvio.EMAIL,
    )
    estado_envio = models.CharField(
        max_length=10,
        choices=EstadoEnvio.choices,
        default=EstadoEnvio.PENDIENTE,
    )
    mensaje = models.TextField(blank=True)
    enviada_en = models.DateTimeField(null=True, blank=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'notificaciones'
        ordering = ['-creada_en']

    def __str__(self):
        return f'{self.get_tipo_display()} para {self.destinatario} - Turno {self.turno_id}'
