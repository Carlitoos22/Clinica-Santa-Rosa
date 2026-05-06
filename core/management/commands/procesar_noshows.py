from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Turno


class Command(BaseCommand):
    help = 'Marca como no-show los turnos pasados sin check-in y verifica bloqueos (RN-04).'

    def handle(self, *args, **options):
        ahora = timezone.now()

        turnos_pasados = Turno.objects.filter(
            fecha_hora__lt=ahora,
            estado__in=[Turno.Estado.RESERVADO, Turno.Estado.CONFIRMADO],
            hora_checkin__isnull=True,
        ).select_related('paciente')

        total = 0
        bloqueados = 0

        for turno in turnos_pasados:
            turno.estado = Turno.Estado.NO_SHOW
            turno.save(update_fields=['estado', 'actualizado_en'])
            total += 1

            if turno.paciente.verificar_bloqueo():
                bloqueados += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Procesados: {total} turnos marcados como no-show, '
                f'{bloqueados} pacientes bloqueados.'
            )
        )
