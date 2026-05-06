from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta
from core.models import Turno, BloqueoHorario
from core.permissions import medico_requerido


@medico_requerido
def agenda_view(request):
    """RF-13 / RF-14 / CU-05: Agenda del día con datos de pacientes."""
    medico = request.user.perfil_medico
    fecha_str = request.GET.get('fecha')
    fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date() if fecha_str else timezone.now().date()

    turnos = Turno.objects.filter(
        medico=medico,
        fecha_hora__date=fecha,
        estado__in=[Turno.Estado.RESERVADO, Turno.Estado.CONFIRMADO],
    ).select_related('paciente__usuario', 'especialidad').order_by('fecha_hora')

    return render(request, 'medicos/agenda.html', {
        'turnos': turnos,
        'fecha': fecha,
        'fecha_anterior': fecha - timedelta(days=1),
        'fecha_siguiente': fecha + timedelta(days=1),
    })


@medico_requerido
def bloquear_horario_view(request):
    """RF-15 / RN-06: Indicar no disponibilidad."""
    medico = request.user.perfil_medico

    if request.method == 'POST':
        fecha_inicio_str = request.POST.get('fecha_inicio')
        fecha_fin_str = request.POST.get('fecha_fin')
        motivo = request.POST.get('motivo', '')

        try:
            fecha_inicio = timezone.make_aware(datetime.strptime(fecha_inicio_str, '%Y-%m-%dT%H:%M'))
            fecha_fin = timezone.make_aware(datetime.strptime(fecha_fin_str, '%Y-%m-%dT%H:%M'))

            bloqueo = BloqueoHorario(
                medico=medico,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                motivo=motivo,
            )
            bloqueo.full_clean()
            bloqueo.save()
            messages.success(request, 'Horario bloqueado exitosamente.')
            return redirect('medicos:mis_bloqueos')
        except Exception as e:
            messages.error(request, str(e))

    return render(request, 'medicos/bloquear_horario.html')


@medico_requerido
def mis_bloqueos_view(request):
    """Lista de bloqueos del médico."""
    medico = request.user.perfil_medico
    bloqueos = BloqueoHorario.objects.filter(
        medico=medico,
        fecha_fin__gte=timezone.now(),
    )
    return render(request, 'medicos/mis_bloqueos.html', {
        'bloqueos': bloqueos,
    })
