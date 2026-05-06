from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from datetime import datetime
from core.models import Especialidad, Turno, Paciente
from core.permissions import paciente_requerido
from core.utils import (
    obtener_medicos_disponibles, reservar_turno, cancelar_turno,
    reprogramar_turno, obtener_slots_disponibles, TurnoError,
)


@paciente_requerido
def mis_turnos_view(request):
    """RF-06: Historial de turnos del paciente."""
    paciente = request.user.perfil_paciente
    turnos_futuros = paciente.turnos.filter(
        fecha_hora__gte=timezone.now(),
        estado__in=[Turno.Estado.RESERVADO, Turno.Estado.CONFIRMADO],
    )
    turnos_pasados = paciente.turnos.filter(
        fecha_hora__lt=timezone.now(),
    )
    return render(request, 'pacientes/mis_turnos.html', {
        'turnos_futuros': turnos_futuros,
        'turnos_pasados': turnos_pasados,
    })


@paciente_requerido
def buscar_especialidad_view(request):
    """RF-01: Buscar especialidades disponibles."""
    especialidades = Especialidad.objects.filter(activa=True)
    return render(request, 'pacientes/buscar_especialidad.html', {
        'especialidades': especialidades,
    })


@paciente_requerido
def seleccionar_turno_view(request, especialidad_id):
    """RF-02: Mostrar médicos y horarios disponibles."""
    especialidad = get_object_or_404(Especialidad, pk=especialidad_id, activa=True)
    fecha_str = request.GET.get('fecha')
    fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date() if fecha_str else timezone.now().date()

    medicos_disponibles = obtener_medicos_disponibles(especialidad, fecha)

    return render(request, 'pacientes/seleccionar_turno.html', {
        'especialidad': especialidad,
        'fecha': fecha,
        'medicos_disponibles': medicos_disponibles,
    })


@paciente_requerido
def reservar_turno_view(request):
    """RF-03: Reservar un turno."""
    if request.method != 'POST':
        return redirect('pacientes:buscar_especialidad')

    paciente = request.user.perfil_paciente
    medico_id = request.POST.get('medico_id')
    especialidad_id = request.POST.get('especialidad_id')
    fecha_hora_str = request.POST.get('fecha_hora')

    try:
        from core.models import Medico
        medico = get_object_or_404(Medico, pk=medico_id)
        especialidad = get_object_or_404(Especialidad, pk=especialidad_id)
        fecha_hora = timezone.make_aware(datetime.strptime(fecha_hora_str, '%Y-%m-%d %H:%M'))

        turno = reservar_turno(
            paciente=paciente,
            medico=medico,
            especialidad=especialidad,
            fecha_hora=fecha_hora,
            canal=Turno.Canal.ONLINE,
            creado_por=request.user,
        )
        messages.success(request, f'Turno reservado exitosamente. ID: {turno.id}')
    except TurnoError as e:
        messages.error(request, str(e))

    return redirect('pacientes:mis_turnos')


@paciente_requerido
def cancelar_turno_view(request, turno_id):
    """RF-04: Cancelar un turno."""
    turno = get_object_or_404(Turno, pk=turno_id, paciente=request.user.perfil_paciente)

    if request.method == 'POST':
        try:
            cancelar_turno(turno)
            messages.success(request, 'Turno cancelado exitosamente.')
        except TurnoError as e:
            messages.error(request, str(e))
        return redirect('pacientes:mis_turnos')

    return render(request, 'pacientes/cancelar_turno.html', {'turno': turno})


@paciente_requerido
def reprogramar_turno_view(request, turno_id):
    """RF-05: Reprogramar un turno."""
    turno = get_object_or_404(Turno, pk=turno_id, paciente=request.user.perfil_paciente)

    if request.method == 'POST':
        fecha_hora_str = request.POST.get('fecha_hora')
        try:
            nueva_fecha = timezone.make_aware(datetime.strptime(fecha_hora_str, '%Y-%m-%d %H:%M'))
            nuevo_turno = reprogramar_turno(turno, nueva_fecha, reprogramado_por=request.user)
            messages.success(request, f'Turno reprogramado. Nuevo ID: {nuevo_turno.id}')
        except TurnoError as e:
            messages.error(request, str(e))
        return redirect('pacientes:mis_turnos')

    # Mostrar slots disponibles del mismo médico
    fecha_str = request.GET.get('fecha')
    fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date() if fecha_str else timezone.now().date()
    slots = obtener_slots_disponibles(turno.medico, fecha)

    return render(request, 'pacientes/reprogramar_turno.html', {
        'turno': turno,
        'slots': slots,
        'fecha': fecha,
    })
