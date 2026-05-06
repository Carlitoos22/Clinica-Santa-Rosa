from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from datetime import datetime, timedelta, time
from .models import (
    Turno, Medico, Paciente, Especialidad,
    DisponibilidadMedica, BloqueoHorario, FamiliarPaciente,
)


class TurnoError(Exception):
    """Excepción base para errores de lógica de turnos."""
    pass


# ---------------------------------------------------------------------------
# Consulta de disponibilidad (RF-02, RN-01)
# ---------------------------------------------------------------------------

def obtener_slots_disponibles(medico, fecha, especialidad=None):
    """
    Genera los slots horarios libres de un médico para una fecha dada.
    Considera: disponibilidad semanal, bloqueos, y turnos ya reservados.
    Retorna lista de objetos datetime (inicio de cada slot libre).
    """
    dia_semana = fecha.weekday()

    disponibilidades = DisponibilidadMedica.objects.filter(
        medico=medico,
        dia_semana=dia_semana,
    )
    if not disponibilidades.exists():
        return []

    fecha_inicio_dia = timezone.make_aware(datetime.combine(fecha, time.min))
    fecha_fin_dia = timezone.make_aware(datetime.combine(fecha, time.max))

    # Verificar si hay bloqueo para ese día
    bloqueos = BloqueoHorario.objects.filter(
        medico=medico,
        fecha_inicio__lt=fecha_fin_dia,
        fecha_fin__gt=fecha_inicio_dia,
    )

    # Turnos activos del médico en esa fecha
    turnos_ocupados = Turno.objects.filter(
        medico=medico,
        fecha_hora__date=fecha,
        estado__in=[Turno.Estado.RESERVADO, Turno.Estado.CONFIRMADO],
    ).values_list('fecha_hora', flat=True)

    horas_ocupadas = set(turnos_ocupados)
    slots_libres = []

    for disp in disponibilidades:
        slot_actual = timezone.make_aware(datetime.combine(fecha, disp.hora_inicio))
        slot_fin_bloque = timezone.make_aware(datetime.combine(fecha, disp.hora_fin))
        duracion = timedelta(minutes=disp.duracion_turno)

        while slot_actual + duracion <= slot_fin_bloque:
            # Verificar que no esté bloqueado
            bloqueado = bloqueos.filter(
                fecha_inicio__lte=slot_actual,
                fecha_fin__gt=slot_actual,
            ).exists()

            if not bloqueado and slot_actual not in horas_ocupadas:
                # No mostrar slots pasados
                if slot_actual > timezone.now():
                    slots_libres.append(slot_actual)

            slot_actual += duracion

    return sorted(slots_libres)


def obtener_medicos_disponibles(especialidad, fecha):
    """
    RF-02: Devuelve médicos con al menos un slot libre para una especialidad y fecha.
    Retorna lista de tuplas (medico, [slots_libres]).
    """
    medicos = Medico.objects.filter(
        especialidades=especialidad,
    ).select_related('usuario')

    resultado = []
    for medico in medicos:
        slots = obtener_slots_disponibles(medico, fecha, especialidad)
        if slots:
            resultado.append((medico, slots))

    return resultado


def buscar_siguiente_fecha_disponible(medico, desde=None, max_dias=30):
    """
    CU-01 flujo alternativo 4a: sugiere la siguiente fecha con disponibilidad.
    """
    if desde is None:
        desde = timezone.now().date()

    for i in range(max_dias):
        fecha = desde + timedelta(days=i)
        slots = obtener_slots_disponibles(medico, fecha)
        if slots:
            return fecha, slots

    return None, []


# ---------------------------------------------------------------------------
# Validaciones de reserva (RN-01, RN-02, RN-04)
# ---------------------------------------------------------------------------

def validar_reserva(paciente, medico, especialidad, fecha_hora):
    """
    Ejecuta todas las validaciones antes de crear un turno.
    Lanza TurnoError con mensaje descriptivo si alguna falla.
    """
    # RN-04: Paciente bloqueado
    if paciente.esta_bloqueado:
        raise TurnoError(
            'El paciente está bloqueado por ausencias reiteradas. '
            'Debe comunicarse con recepción.'
        )

    # RN-01: No doble reserva en el mismo slot para el mismo médico
    if Turno.objects.filter(
        medico=medico,
        fecha_hora=fecha_hora,
        estado__in=[Turno.Estado.RESERVADO, Turno.Estado.CONFIRMADO],
    ).exists():
        raise TurnoError('El horario seleccionado ya no está disponible.')

    # RN-02: Paciente no puede tener dos turnos simultáneos
    if Turno.objects.filter(
        paciente=paciente,
        fecha_hora=fecha_hora,
        estado__in=[Turno.Estado.RESERVADO, Turno.Estado.CONFIRMADO],
    ).exists():
        raise TurnoError(
            'Ya tenés un turno en ese horario con otra especialidad.'
        )

    # Validar que la especialidad pertenezca al médico
    if not medico.especialidades.filter(pk=especialidad.pk).exists():
        raise TurnoError('El médico no atiende esa especialidad.')

    # Validar que el horario no esté bloqueado
    if BloqueoHorario.objects.filter(
        medico=medico,
        fecha_inicio__lte=fecha_hora,
        fecha_fin__gt=fecha_hora,
    ).exists():
        raise TurnoError('El médico no está disponible en ese horario.')

    # Validar que sea un horario futuro
    if fecha_hora <= timezone.now():
        raise TurnoError('No se puede reservar un turno en el pasado.')


# ---------------------------------------------------------------------------
# Reserva de turnos (RF-03, RF-08, RF-22)
# ---------------------------------------------------------------------------

@transaction.atomic
def reservar_turno(paciente, medico, especialidad, fecha_hora,
                   canal=Turno.Canal.ONLINE, creado_por=None):
    """
    RF-03/RF-08: Crea un turno validado.
    RF-22: Registra automáticamente el canal de origen.
    Retorna el turno creado.
    """
    validar_reserva(paciente, medico, especialidad, fecha_hora)

    turno = Turno.objects.create(
        paciente=paciente,
        medico=medico,
        especialidad=especialidad,
        fecha_hora=fecha_hora,
        canal=canal,
        creado_por=creado_por,
    )
    return turno


@transaction.atomic
def reservar_turno_familiar(paciente, familiar, medico, especialidad,
                            fecha_hora, canal=Turno.Canal.ONLINE, creado_por=None):
    """
    RF-07 / RN-08: Reserva un turno para un familiar del paciente.
    Valida que el familiar esté registrado y no bloqueado.
    """
    if not FamiliarPaciente.objects.filter(
        pk=familiar.pk,
        paciente=paciente,
    ).exists():
        raise TurnoError('El familiar no está registrado para este paciente.')

    validar_reserva(paciente, medico, especialidad, fecha_hora)

    turno = Turno.objects.create(
        paciente=paciente,
        medico=medico,
        especialidad=especialidad,
        fecha_hora=fecha_hora,
        canal=canal,
        familiar=familiar,
        creado_por=creado_por,
    )
    return turno


# ---------------------------------------------------------------------------
# Cancelación (RF-04, RF-09, RN-03, RN-05)
# ---------------------------------------------------------------------------

@transaction.atomic
def cancelar_turno(turno, cancelado_por=None):
    """
    RF-04/RF-09: Cancela un turno existente.
    RN-03: Si faltan menos de 2 horas, se registra como no-show.
    RN-05: El slot se libera automáticamente al cambiar el estado.
    Retorna el turno actualizado.
    """
    if turno.estado not in (Turno.Estado.RESERVADO, Turno.Estado.CONFIRMADO):
        raise TurnoError('Solo se pueden cancelar turnos reservados o confirmados.')

    if not turno.puede_cancelar:
        # RN-03: Menos de 2 horas → se registra como no-show
        return marcar_noshow(turno)

    turno.estado = Turno.Estado.CANCELADO
    turno.save(update_fields=['estado', 'actualizado_en'])
    return turno


# ---------------------------------------------------------------------------
# Reprogramación (RF-05)
# ---------------------------------------------------------------------------

@transaction.atomic
def reprogramar_turno(turno, nueva_fecha_hora, reprogramado_por=None):
    """
    RF-05: Cancela el turno actual y crea uno nuevo en el horario disponible.
    Valida disponibilidad del nuevo slot y libera el anterior.
    Retorna el nuevo turno.
    """
    if turno.estado not in (Turno.Estado.RESERVADO, Turno.Estado.CONFIRMADO):
        raise TurnoError('Solo se pueden reprogramar turnos reservados o confirmados.')

    if nueva_fecha_hora <= timezone.now():
        raise TurnoError('No se puede reprogramar a un horario pasado.')

    # Validar nuevo slot
    validar_reserva(
        turno.paciente, turno.medico, turno.especialidad, nueva_fecha_hora,
    )

    # Cancelar el turno anterior
    turno.estado = Turno.Estado.CANCELADO
    turno.save(update_fields=['estado', 'actualizado_en'])

    # Crear nuevo turno
    nuevo_turno = Turno.objects.create(
        paciente=turno.paciente,
        medico=turno.medico,
        especialidad=turno.especialidad,
        fecha_hora=nueva_fecha_hora,
        canal=turno.canal,
        familiar=turno.familiar,
        creado_por=reprogramado_por,
    )
    return nuevo_turno


# ---------------------------------------------------------------------------
# Check-in (RF-10)
# ---------------------------------------------------------------------------

def registrar_checkin(turno):
    """
    RF-10: Marca el check-in del paciente, registrando hora de llegada.
    """
    if turno.estado not in (Turno.Estado.RESERVADO, Turno.Estado.CONFIRMADO):
        raise TurnoError('El turno no está en un estado válido para check-in.')

    if turno.fecha_hora.date() != timezone.now().date():
        raise TurnoError('Solo se puede hacer check-in el día del turno.')

    turno.hora_checkin = timezone.now()
    turno.estado = Turno.Estado.CONFIRMADO
    turno.save(update_fields=['hora_checkin', 'estado', 'actualizado_en'])
    return turno


# ---------------------------------------------------------------------------
# No-Show (RF-11, RN-04)
# ---------------------------------------------------------------------------

@transaction.atomic
def marcar_noshow(turno):
    """
    RF-11: Marca un turno como no-show.
    RN-04: Verifica si el paciente debe ser bloqueado (3 no-shows en 60 días).
    RN-05: Libera el horario automáticamente.
    """
    if turno.estado not in (Turno.Estado.RESERVADO, Turno.Estado.CONFIRMADO):
        raise TurnoError('Solo se pueden marcar como no-show turnos reservados o confirmados.')

    turno.estado = Turno.Estado.NO_SHOW
    turno.save(update_fields=['estado', 'actualizado_en'])

    # RN-04: Verificar bloqueo
    turno.paciente.verificar_bloqueo()

    return turno


# ---------------------------------------------------------------------------
# Marcar como atendido
# ---------------------------------------------------------------------------

def marcar_atendido(turno):
    """Marca el turno como atendido después de la consulta."""
    if turno.estado != Turno.Estado.CONFIRMADO:
        raise TurnoError('Solo se pueden marcar como atendidos turnos con check-in.')

    turno.estado = Turno.Estado.ATENDIDO
    turno.save(update_fields=['estado', 'actualizado_en'])
    return turno


# ---------------------------------------------------------------------------
# Búsqueda (RF-12)
# ---------------------------------------------------------------------------

def buscar_turnos(query=None, fecha=None, medico=None, especialidad=None, estado=None):
    """
    RF-12: Búsqueda de turnos por nombre, DNI o fecha.
    Retorna un queryset filtrado.
    """
    qs = Turno.objects.select_related(
        'paciente__usuario', 'medico__usuario', 'especialidad',
    )

    if query:
        qs = qs.filter(
            Q(paciente__usuario__first_name__icontains=query) |
            Q(paciente__usuario__last_name__icontains=query) |
            Q(paciente__usuario__dni__icontains=query)
        )

    if fecha:
        qs = qs.filter(fecha_hora__date=fecha)

    if medico:
        qs = qs.filter(medico=medico)

    if especialidad:
        qs = qs.filter(especialidad=especialidad)

    if estado:
        qs = qs.filter(estado=estado)

    return qs
