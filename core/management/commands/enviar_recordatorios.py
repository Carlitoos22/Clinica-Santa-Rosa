from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import Notificacion


class Command(BaseCommand):
    help = 'Envía recordatorios pendientes para turnos en las próximas 24 horas (RN-07).'

    def handle(self, *args, **options):
        ahora = timezone.now()
        limite = ahora + timedelta(hours=24)

        recordatorios = Notificacion.objects.filter(
            tipo=Notificacion.Tipo.RECORDATORIO,
            estado_envio=Notificacion.EstadoEnvio.PENDIENTE,
            turno__fecha_hora__gte=ahora,
            turno__fecha_hora__lte=limite,
            turno__estado__in=['reservado', 'confirmado'],
        ).select_related('turno', 'destinatario')

        enviados = 0
        for notif in recordatorios:
            # Aquí iría la integración real con email/SMS/WhatsApp
            notif.estado_envio = Notificacion.EstadoEnvio.ENVIADA
            notif.enviada_en = ahora
            notif.save(update_fields=['estado_envio', 'enviada_en'])
            enviados += 1

        self.stdout.write(
            self.style.SUCCESS(f'{enviados} recordatorios enviados.')
        )
