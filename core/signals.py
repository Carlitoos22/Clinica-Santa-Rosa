from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Turno, Notificacion


@receiver(post_save, sender=Turno)
def turno_post_save(sender, instance, created, **kwargs):
    if created:
        _notificar_confirmacion(instance)
        _crear_recordatorio(instance)
    else:
        if instance.estado == Turno.Estado.CANCELADO:
            _notificar_cancelacion_medico(instance)


def _notificar_confirmacion(turno):
    """RF-23: Notificación de confirmación al paciente al reservar."""
    Notificacion.objects.create(
        turno=turno,
        destinatario=turno.paciente.usuario,
        tipo=Notificacion.Tipo.CONFIRMACION,
        mensaje=(
            f'Tu turno fue confirmado: {turno.especialidad.nombre} con '
            f'{turno.medico} el {turno.fecha_hora:%d/%m/%Y a las %H:%M}hs. '
            f'ID de turno: {turno.id}'
        ),
    )


def _notificar_cancelacion_medico(turno):
    """RF-16: Notificar al médico cuando un turno propio sea cancelado."""
    Notificacion.objects.create(
        turno=turno,
        destinatario=turno.medico.usuario,
        tipo=Notificacion.Tipo.CANCELACION,
        mensaje=(
            f'El turno del {turno.fecha_hora:%d/%m/%Y a las %H:%M}hs '
            f'con {turno.paciente} fue cancelado.'
        ),
    )


def _crear_recordatorio(turno):
    """RN-07: Recordatorio automático 24 horas antes del turno."""
    Notificacion.objects.create(
        turno=turno,
        destinatario=turno.paciente.usuario,
        tipo=Notificacion.Tipo.RECORDATORIO,
        mensaje=(
            f'Recordatorio: tenés un turno mañana {turno.fecha_hora:%d/%m/%Y} '
            f'a las {turno.fecha_hora:%H:%M}hs con {turno.medico} '
            f'({turno.especialidad.nombre}).'
        ),
    )
