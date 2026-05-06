from django.db.models import Count, Q, F
from django.utils import timezone
from datetime import timedelta, datetime, time
from core.models import Turno, Medico, Especialidad, DisponibilidadMedica


ESTADOS_ACTIVOS = [
    Turno.Estado.RESERVADO,
    Turno.Estado.CONFIRMADO,
    Turno.Estado.ATENDIDO,
    Turno.Estado.NO_SHOW,
]


# ---------------------------------------------------------------------------
# RF-17: Reporte de ocupación por médico
# ---------------------------------------------------------------------------

def _calcular_slots_totales(medico, fecha_desde, fecha_hasta):
    """Calcula cuántos slots tuvo disponibles un médico en un rango de fechas."""
    disponibilidades = DisponibilidadMedica.objects.filter(medico=medico)
    if not disponibilidades.exists():
        return 0

    total_slots = 0
    dia_actual = fecha_desde

    while dia_actual <= fecha_hasta:
        disps_del_dia = disponibilidades.filter(dia_semana=dia_actual.weekday())
        for disp in disps_del_dia:
            inicio = datetime.combine(dia_actual, disp.hora_inicio)
            fin = datetime.combine(dia_actual, disp.hora_fin)
            duracion = timedelta(minutes=disp.duracion_turno)
            while inicio + duracion <= fin:
                total_slots += 1
                inicio += duracion
        dia_actual += timedelta(days=1)

    return total_slots


def reporte_ocupacion_por_medico(fecha_desde, fecha_hasta):
    """
    RF-17: Porcentaje de turnos tomados vs disponibles por médico.
    Retorna lista de dicts con datos de cada médico.
    """
    medicos = Medico.objects.select_related('usuario').all()
    resultado = []

    for medico in medicos:
        slots_totales = _calcular_slots_totales(medico, fecha_desde, fecha_hasta)
        turnos_tomados = Turno.objects.filter(
            medico=medico,
            fecha_hora__date__gte=fecha_desde,
            fecha_hora__date__lte=fecha_hasta,
            estado__in=ESTADOS_ACTIVOS,
        ).count()

        porcentaje = (turnos_tomados / slots_totales * 100) if slots_totales > 0 else 0

        resultado.append({
            'medico': str(medico),
            'medico_id': medico.id,
            'slots_totales': slots_totales,
            'turnos_tomados': turnos_tomados,
            'slots_libres': max(slots_totales - turnos_tomados, 0),
            'porcentaje_ocupacion': round(porcentaje, 1),
        })

    return sorted(resultado, key=lambda x: x['porcentaje_ocupacion'], reverse=True)


# ---------------------------------------------------------------------------
# RF-18: Reporte de ocupación por especialidad
# ---------------------------------------------------------------------------

def reporte_ocupacion_por_especialidad(fecha_desde, fecha_hasta):
    """
    RF-18: Porcentaje de ocupación agrupado por especialidad.
    """
    especialidades = Especialidad.objects.filter(activa=True)
    resultado = []

    for esp in especialidades:
        medicos_esp = Medico.objects.filter(especialidades=esp)
        slots_totales = sum(
            _calcular_slots_totales(m, fecha_desde, fecha_hasta)
            for m in medicos_esp
        )
        turnos_tomados = Turno.objects.filter(
            especialidad=esp,
            fecha_hora__date__gte=fecha_desde,
            fecha_hora__date__lte=fecha_hasta,
            estado__in=ESTADOS_ACTIVOS,
        ).count()

        porcentaje = (turnos_tomados / slots_totales * 100) if slots_totales > 0 else 0

        resultado.append({
            'especialidad': esp.nombre,
            'especialidad_id': esp.id,
            'medicos_count': medicos_esp.count(),
            'slots_totales': slots_totales,
            'turnos_tomados': turnos_tomados,
            'porcentaje_ocupacion': round(porcentaje, 1),
        })

    return sorted(resultado, key=lambda x: x['porcentaje_ocupacion'], reverse=True)


# ---------------------------------------------------------------------------
# RF-19: Reporte de tasa de ausentismo
# ---------------------------------------------------------------------------

def reporte_ausentismo(fecha_desde, fecha_hasta, medico=None, especialidad=None):
    """
    RF-19: Tasa de ausentismo global y segmentado por médico o especialidad.
    Retorna dict con totales y porcentaje.
    """
    filtros = Q(
        fecha_hora__date__gte=fecha_desde,
        fecha_hora__date__lte=fecha_hasta,
        estado__in=ESTADOS_ACTIVOS,
    )

    if medico:
        filtros &= Q(medico=medico)
    if especialidad:
        filtros &= Q(especialidad=especialidad)

    turnos = Turno.objects.filter(filtros)
    total = turnos.count()
    noshows = turnos.filter(estado=Turno.Estado.NO_SHOW).count()
    tasa = (noshows / total * 100) if total > 0 else 0

    resultado = {
        'total_turnos': total,
        'no_shows': noshows,
        'atendidos': turnos.filter(estado=Turno.Estado.ATENDIDO).count(),
        'tasa_ausentismo': round(tasa, 1),
    }

    # Desglose por médico si no se filtró por uno específico
    if not medico:
        resultado['por_medico'] = _ausentismo_por_medico(fecha_desde, fecha_hasta, especialidad)

    # Desglose por especialidad si no se filtró por una específica
    if not especialidad:
        resultado['por_especialidad'] = _ausentismo_por_especialidad(fecha_desde, fecha_hasta, medico)

    return resultado


def _ausentismo_por_medico(fecha_desde, fecha_hasta, especialidad=None):
    filtros = Q(
        turnos__fecha_hora__date__gte=fecha_desde,
        turnos__fecha_hora__date__lte=fecha_hasta,
        turnos__estado__in=ESTADOS_ACTIVOS,
    )
    if especialidad:
        filtros &= Q(turnos__especialidad=especialidad)

    return list(
        Medico.objects.filter(filtros)
        .annotate(
            total=Count('turnos', filter=Q(
                turnos__fecha_hora__date__gte=fecha_desde,
                turnos__fecha_hora__date__lte=fecha_hasta,
                turnos__estado__in=ESTADOS_ACTIVOS,
            )),
            noshows=Count('turnos', filter=Q(
                turnos__fecha_hora__date__gte=fecha_desde,
                turnos__fecha_hora__date__lte=fecha_hasta,
                turnos__estado=Turno.Estado.NO_SHOW,
            )),
        )
        .values('usuario__first_name', 'usuario__last_name', 'total', 'noshows')
    )


def _ausentismo_por_especialidad(fecha_desde, fecha_hasta, medico=None):
    filtros = Q(
        turnos__fecha_hora__date__gte=fecha_desde,
        turnos__fecha_hora__date__lte=fecha_hasta,
        turnos__estado__in=ESTADOS_ACTIVOS,
    )
    if medico:
        filtros &= Q(turnos__medico=medico)

    return list(
        Especialidad.objects.filter(filtros)
        .annotate(
            total=Count('turnos', filter=Q(
                turnos__fecha_hora__date__gte=fecha_desde,
                turnos__fecha_hora__date__lte=fecha_hasta,
                turnos__estado__in=ESTADOS_ACTIVOS,
            )),
            noshows=Count('turnos', filter=Q(
                turnos__fecha_hora__date__gte=fecha_desde,
                turnos__fecha_hora__date__lte=fecha_hasta,
                turnos__estado=Turno.Estado.NO_SHOW,
            )),
        )
        .values('nombre', 'total', 'noshows')
    )


# ---------------------------------------------------------------------------
# RF-20: Turnos por canal (online vs teléfono vs presencial)
# ---------------------------------------------------------------------------

def reporte_turnos_por_canal(fecha_desde, fecha_hasta):
    """
    RF-20: Cantidad de turnos tomados por canal para medir impacto del sistema.
    """
    turnos = Turno.objects.filter(
        fecha_hora__date__gte=fecha_desde,
        fecha_hora__date__lte=fecha_hasta,
        estado__in=ESTADOS_ACTIVOS,
    )

    total = turnos.count()
    por_canal = list(
        turnos.values('canal')
        .annotate(cantidad=Count('id'))
        .order_by('-cantidad')
    )

    for item in por_canal:
        item['canal_display'] = dict(Turno.Canal.choices).get(item['canal'], item['canal'])
        item['porcentaje'] = round(item['cantidad'] / total * 100, 1) if total > 0 else 0

    return {
        'total': total,
        'por_canal': por_canal,
    }
