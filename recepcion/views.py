import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from datetime import datetime
from authentication.models import Usuario
from core.models import Turno, Medico, Especialidad, Paciente
from core.permissions import recepcionista_requerido, recepcion_o_admin
from core.utils import (
    reservar_turno, cancelar_turno, reprogramar_turno,
    registrar_checkin, marcar_noshow, marcar_atendido,
    buscar_turnos, obtener_medicos_disponibles, TurnoError,
)


@recepcionista_requerido
def panel_view(request):
    """Panel principal de recepción con turnos del día."""
    from datetime import timedelta
    fecha_str = request.GET.get('fecha')
    fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date() if fecha_str else timezone.now().date()

    turnos_hoy = Turno.objects.filter(
        fecha_hora__date=fecha,
    ).select_related(
        'paciente__usuario', 'medico__usuario', 'especialidad',
    ).order_by('fecha_hora').distinct()

    return render(request, 'recepcion/panel.html', {
        'turnos_hoy': turnos_hoy,
        'fecha': fecha,
        'fecha_anterior': fecha - timedelta(days=1),
        'fecha_siguiente': fecha + timedelta(days=1),
    })


@recepcionista_requerido
def registrar_turno_telefonico_view(request):
    """RF-08 / CU-03: Registro rápido de turno telefónico."""
    especialidades = Especialidad.objects.filter(activa=True)
    medicos = Medico.objects.select_related('usuario').all()

    if request.method == 'POST':
        dni = request.POST.get('dni', '').strip()
        medico_id = request.POST.get('medico_id')
        especialidad_id = request.POST.get('especialidad_id')
        fecha_hora_str = request.POST.get('fecha_hora', '')
        nombre = request.POST.get('nombre', '').strip()
        apellido = request.POST.get('apellido', '').strip()
        celular = request.POST.get('celular', '').strip()

        try:
            paciente = Paciente.objects.filter(usuario__dni=dni).first()

            if not paciente:
                if not nombre or not apellido:
                    messages.warning(request, f'No se encontró un paciente con DNI {dni}. Completá nombre y apellido para registrarlo.')
                    return render(request, 'recepcion/registrar_telefonico.html', {
                        'especialidades': especialidades,
                        'medicos': medicos,
                        'mostrar_datos_paciente': True,
                        'dni': dni,
                        'nombre': nombre,
                        'apellido': apellido,
                        'celular': celular,
                        'medico_id': medico_id,
                        'especialidad_id': especialidad_id,
                        'fecha_hora': fecha_hora_str,
                    })

                errores = []
                if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]+$', nombre):
                    errores.append('El nombre solo puede contener letras.')
                if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]+$', apellido):
                    errores.append('El apellido solo puede contener letras.')
                if celular and not re.match(r'^\+?\d{7,15}$', celular):
                    errores.append('El celular debe contener solo números (7 a 15 dígitos).')
                if not re.match(r'^\d{7,8}$', dni):
                    errores.append('El DNI debe contener solo números (7 u 8 dígitos).')

                if errores:
                    for err in errores:
                        messages.error(request, err)
                    return render(request, 'recepcion/registrar_telefonico.html', {
                        'especialidades': especialidades,
                        'medicos': medicos,
                        'mostrar_datos_paciente': True,
                        'dni': dni,
                        'nombre': nombre,
                        'apellido': apellido,
                        'celular': celular,
                        'medico_id': medico_id,
                        'especialidad_id': especialidad_id,
                        'fecha_hora': fecha_hora_str,
                    })

                usuario = Usuario.objects.create_user(
                    username=f'pac_{dni}',
                    first_name=nombre,
                    last_name=apellido,
                    dni=dni,
                    celular=celular,
                    rol=Usuario.Rol.PACIENTE,
                    password=f'clinica{dni}',
                )
                paciente = Paciente.objects.create(usuario=usuario)
                messages.info(request, f'Paciente {nombre} {apellido} registrado. Usuario: pac_{dni} / Contraseña: clinica{dni}')

            medico = get_object_or_404(Medico, pk=medico_id)
            especialidad = get_object_or_404(Especialidad, pk=especialidad_id)
            fecha_hora_str = fecha_hora_str.replace('T', ' ')
            fecha_hora = timezone.make_aware(datetime.strptime(fecha_hora_str, '%Y-%m-%d %H:%M'))

            turno = reservar_turno(
                paciente=paciente,
                medico=medico,
                especialidad=especialidad,
                fecha_hora=fecha_hora,
                canal=Turno.Canal.TELEFONO,
                creado_por=request.user,
            )
            messages.success(request, f'Turno telefónico registrado. ID: {turno.id}')
            return redirect('recepcion:panel')
        except TurnoError as e:
            messages.error(request, str(e))
        except (ValueError, TypeError):
            messages.error(request, 'Datos inválidos. Verificá el DNI, médico y horario.')

    return render(request, 'recepcion/registrar_telefonico.html', {
        'especialidades': especialidades,
        'medicos': medicos,
    })


@recepcionista_requerido
def checkin_view(request, turno_id):
    """RF-10 / CU-04: Check-in del paciente."""
    turno = get_object_or_404(Turno, pk=turno_id)

    if request.method == 'POST':
        try:
            registrar_checkin(turno)
            messages.success(request, f'Check-in registrado para {turno.paciente}.')
        except TurnoError as e:
            messages.error(request, str(e))

    return redirect('recepcion:panel')


@recepcionista_requerido
def noshow_view(request, turno_id):
    """RF-11 / CU-04: Marcar turno como no-show."""
    turno = get_object_or_404(Turno, pk=turno_id)

    if request.method == 'POST':
        try:
            marcar_noshow(turno)
            paciente = turno.paciente
            msg = f'Turno marcado como no-show.'
            if paciente.esta_bloqueado:
                msg += f' El paciente {paciente} fue bloqueado por ausencias reiteradas.'
            messages.warning(request, msg)
        except TurnoError as e:
            messages.error(request, str(e))

    return redirect('recepcion:panel')


@recepcionista_requerido
def atendido_view(request, turno_id):
    """Marcar turno como atendido."""
    turno = get_object_or_404(Turno, pk=turno_id)

    if request.method == 'POST':
        try:
            marcar_atendido(turno)
            messages.success(request, 'Turno marcado como atendido.')
        except TurnoError as e:
            messages.error(request, str(e))

    return redirect('recepcion:panel')


@recepcionista_requerido
def cancelar_turno_recepcion_view(request, turno_id):
    """RF-09: Cancelar turno a pedido del paciente."""
    turno = get_object_or_404(Turno, pk=turno_id)

    if request.method == 'POST':
        try:
            cancelar_turno(turno)
            messages.success(request, 'Turno cancelado exitosamente.')
        except TurnoError as e:
            messages.error(request, str(e))
        return redirect('recepcion:panel')

    return render(request, 'recepcion/cancelar_turno.html', {'turno': turno})


@recepcion_o_admin
def buscar_turnos_view(request):
    """RF-12: Búsqueda de turnos por nombre, DNI o fecha."""
    query = request.GET.get('q', '')
    fecha_str = request.GET.get('fecha', '')
    fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date() if fecha_str else None

    turnos = buscar_turnos(query=query or None, fecha=fecha) if (query or fecha) else Turno.objects.none()

    return render(request, 'recepcion/buscar_turnos.html', {
        'turnos': turnos,
        'query': query,
        'fecha': fecha_str,
    })
