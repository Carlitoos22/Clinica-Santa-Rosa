# Documentación Técnica — Sistema de Gestión de Turnos

## Índice

1. [Arquitectura general](#1-arquitectura-general)
2. [Modelos de datos](#2-modelos-de-datos)
3. [Lógica de negocio](#3-lógica-de-negocio)
4. [Signals y automatizaciones](#4-signals-y-automatizaciones)
5. [Sistema de permisos](#5-sistema-de-permisos)
6. [Reportes y estadísticas](#6-reportes-y-estadísticas)
7. [Vistas y URLs](#7-vistas-y-urls)
8. [Templates](#8-templates)
9. [Comandos de gestión](#9-comandos-de-gestión)
10. [Trazabilidad con el ERS](#10-trazabilidad-con-el-ers)

---

## 1. Arquitectura general

El sistema sigue la arquitectura **MTV (Model-Template-View)** de Django, que es equivalente a MVC:

- **Model** → Modelos de datos en `models.py` (equivalente al Modelo en MVC)
- **Template** → Archivos HTML en `templates/` (equivalente a la Vista en MVC)
- **View** → Funciones en `views.py` (equivalente al Controlador en MVC)

### Flujo de una petición

```
Navegador → URLs (urls.py) → Vista (views.py) → Lógica (utils.py) → Modelo (models.py)
                                                                          ↓
Navegador ← Template (HTML) ← Vista (views.py) ←←←←←←←←←←←←←←←← Base de datos
```

### Organización en apps

El proyecto se divide en aplicaciones Django independientes, cada una con una responsabilidad clara:

| App | Responsabilidad |
|-----|----------------|
| `authentication` | Modelo de usuario, login, registro, logout |
| `core` | Modelos del dominio, lógica de negocio, signals, permisos |
| `pacientes` | Vistas y URLs para el actor Paciente |
| `recepcion` | Vistas y URLs para el actor Recepcionista |
| `medicos` | Vistas y URLs para el actor Médico |
| `reportes` | Vistas, URLs y lógica de reportes para el Administrador |
| `notifications` | App reservada para integración futura con servicios de notificación |

---

## 2. Modelos de datos

### Archivo: `authentication/models.py`

#### Usuario

Extiende `AbstractUser` de Django para agregar campos específicos del dominio.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `username` | CharField | Heredado de AbstractUser, nombre de usuario para login |
| `password` | CharField | Heredado de AbstractUser, contraseña hasheada |
| `first_name` | CharField | Heredado, nombre del usuario |
| `last_name` | CharField | Heredado, apellido del usuario |
| `email` | EmailField | Heredado, correo electrónico |
| `rol` | CharField(choices) | Rol del usuario: paciente, recepcionista, medico, admin |
| `dni` | CharField(unique) | Documento Nacional de Identidad, único en el sistema |
| `celular` | CharField | Número de celular, opcional |

Se define `AUTH_USER_MODEL = 'authentication.Usuario'` en `settings.py` para que Django use este modelo en lugar del usuario por defecto.

---

### Archivo: `core/models.py`

#### Especialidad

Representa las 6 especialidades médicas de la clínica.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `nombre` | CharField(unique) | Nombre de la especialidad |
| `descripcion` | TextField | Descripción de la especialidad |
| `activa` | BooleanField | Si la especialidad está habilitada |

#### Medico

Perfil del profesional médico, vinculado 1 a 1 con Usuario.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `usuario` | OneToOneField(Usuario) | Relación con el usuario del sistema |
| `matricula` | CharField(unique) | Matrícula profesional |
| `especialidades` | ManyToManyField(Especialidad) | Especialidades que atiende (puede ser más de una) |

La relación ManyToMany permite que un médico atienda múltiples especialidades y que una especialidad tenga múltiples médicos.

#### Paciente

Perfil del paciente con estado de bloqueo.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `usuario` | OneToOneField(Usuario) | Relación con el usuario del sistema |
| `estado` | CharField(choices) | `activo` o `bloqueado` |

**Métodos importantes:**
- `esta_bloqueado` (property): Retorna True si el paciente está bloqueado.
- `contar_noshows_recientes()`: Cuenta los no-shows en los últimos 60 días.
- `verificar_bloqueo()`: Evalúa si el paciente debe ser bloqueado (RN-04). Si tiene 3+ no-shows en 60 días, cambia el estado a `bloqueado` y retorna True.

#### FamiliarPaciente

Permite que un paciente registre familiares para reservar turnos en su nombre (RF-07).

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `paciente` | ForeignKey(Paciente) | Paciente titular |
| `nombre` | CharField | Nombre del familiar |
| `dni` | CharField | DNI del familiar |
| `parentesco` | CharField(choices) | Relación: hijo/a, cónyuge, padre/madre |

Restricción: `unique_together = ['paciente', 'dni']` — un paciente no puede registrar dos veces el mismo familiar.

#### DisponibilidadMedica

Define los horarios semanales en que un médico atiende.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `medico` | ForeignKey(Medico) | Médico al que pertenece |
| `dia_semana` | IntegerField(choices) | 0=Lunes, 1=Martes, ..., 5=Sábado |
| `hora_inicio` | TimeField | Hora de inicio del bloque |
| `hora_fin` | TimeField | Hora de fin del bloque |
| `duracion_turno` | PositiveIntegerField | Duración de cada turno en minutos (default: 30) |

Validación: `hora_inicio` debe ser anterior a `hora_fin`.

#### BloqueoHorario

Períodos de no disponibilidad del médico (vacaciones, congresos). Implementa RF-15 y RN-06.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `medico` | ForeignKey(Medico) | Médico que bloquea |
| `fecha_inicio` | DateTimeField | Inicio del bloqueo |
| `fecha_fin` | DateTimeField | Fin del bloqueo |
| `motivo` | CharField | Motivo del bloqueo (opcional) |

#### Turno

Modelo central del sistema. Representa una cita médica.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `paciente` | ForeignKey(Paciente) | Paciente que reserva |
| `medico` | ForeignKey(Medico) | Médico asignado |
| `especialidad` | ForeignKey(Especialidad) | Especialidad de la consulta |
| `fecha_hora` | DateTimeField | Fecha y hora del turno |
| `duracion` | PositiveIntegerField | Duración en minutos (default: 30) |
| `estado` | CharField(choices) | reservado, confirmado, cancelado, atendido, no_show |
| `canal` | CharField(choices) | online, telefono, presencial |
| `familiar` | ForeignKey(FamiliarPaciente) | Si el turno es para un familiar (nullable) |
| `hora_checkin` | DateTimeField | Hora de llegada del paciente (nullable) |
| `creado_por` | ForeignKey(Usuario) | Usuario que creó el turno |
| `creado_en` | DateTimeField(auto_now_add) | Fecha de creación automática |
| `actualizado_en` | DateTimeField(auto_now) | Fecha de última modificación |

**Índices de base de datos:**
- `(medico, fecha_hora)` — Optimiza consultas de agenda del médico
- `(paciente, fecha_hora)` — Optimiza consultas de turnos del paciente
- `(estado)` — Optimiza filtros por estado

**Properties:**
- `fecha_hora_fin`: Calcula la hora de fin sumando la duración.
- `puede_cancelar`: Retorna True si faltan más de 2 horas para el turno (RN-03).
- `es_futuro`: Retorna True si el turno es futuro.

#### Notificacion

Registra las comunicaciones enviadas al paciente o médico.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `turno` | ForeignKey(Turno) | Turno asociado |
| `destinatario` | ForeignKey(Usuario) | Usuario que recibe la notificación |
| `tipo` | CharField(choices) | recordatorio, confirmacion, cancelacion, no_show |
| `canal_envio` | CharField(choices) | email, sms, whatsapp |
| `estado_envio` | CharField(choices) | pendiente, enviada, fallida |
| `mensaje` | TextField | Contenido del mensaje |
| `enviada_en` | DateTimeField | Momento del envío (nullable) |
| `creada_en` | DateTimeField(auto_now_add) | Momento de creación |

### Diagrama de relaciones

```
Usuario (1) ──── (1) Medico ──── (*) Especialidad
   │                  │
   │                  ├── (*) DisponibilidadMedica
   │                  ├── (*) BloqueoHorario
   │                  └── (*) Turno
   │                            │
   └──── (1) Paciente ─── (*) Turno
               │               │
               ├── (*) FamiliarPaciente
               │               │
               │         Turno.familiar ──→ FamiliarPaciente
               │
               └── estado: activo/bloqueado (RN-04)

Turno (*) ──── (*) Notificacion ──→ Usuario (destinatario)
```

---

## 3. Lógica de negocio

### Archivo: `core/utils.py`

Toda la lógica de negocio está centralizada en este archivo, separada de las vistas para facilitar testing y mantenimiento.

#### TurnoError

Excepción personalizada que se lanza cuando una operación de turno falla. Las vistas la capturan y muestran el mensaje al usuario.

#### obtener_slots_disponibles(medico, fecha, especialidad=None)

Genera los horarios libres de un médico para una fecha específica.

**Algoritmo:**
1. Obtiene las disponibilidades del médico para el día de la semana correspondiente
2. Consulta los bloqueos activos para ese día
3. Consulta los turnos ya reservados/confirmados para ese día
4. Recorre cada bloque de disponibilidad generando slots según la duración configurada
5. Filtra: descarta slots bloqueados, ocupados y pasados
6. Retorna la lista ordenada de datetimes disponibles

#### obtener_medicos_disponibles(especialidad, fecha)

Busca todos los médicos de una especialidad que tengan al menos un slot libre en la fecha dada. Retorna lista de tuplas `(medico, [slots])`.

#### buscar_siguiente_fecha_disponible(medico, desde=None, max_dias=30)

Implementa el flujo alternativo 4a del CU-01: si no hay horarios disponibles para la fecha seleccionada, busca la siguiente fecha con disponibilidad dentro de los próximos 30 días.

#### validar_reserva(paciente, medico, especialidad, fecha_hora)

Ejecuta todas las validaciones antes de crear un turno:

1. **RN-04**: Verifica que el paciente no esté bloqueado
2. **RN-01**: Verifica que no exista otro turno en el mismo slot para el mismo médico
3. **RN-02**: Verifica que el paciente no tenga otro turno simultáneo
4. Verifica que la especialidad pertenezca al médico
5. Verifica que el horario no esté bloqueado
6. Verifica que sea un horario futuro

Lanza `TurnoError` con mensaje descriptivo si alguna validación falla.

#### reservar_turno(paciente, medico, especialidad, fecha_hora, canal, creado_por)

Crea un turno validado. Usa `@transaction.atomic` para garantizar que la validación y la creación sean atómicas (si falla una, no se ejecuta la otra). Registra automáticamente el canal de origen (RF-22).

#### reservar_turno_familiar(paciente, familiar, medico, especialidad, fecha_hora, canal, creado_por)

Variante de reserva para familiares (RF-07, RN-08). Valida que el familiar esté registrado para ese paciente antes de crear el turno.

#### cancelar_turno(turno, cancelado_por)

Cancela un turno existente:
- Si faltan más de 2 horas: cambia el estado a `cancelado` (RN-05: libera el slot)
- Si faltan menos de 2 horas: llama a `marcar_noshow()` (RN-03)

#### reprogramar_turno(turno, nueva_fecha_hora, reprogramado_por)

Cancela el turno actual y crea uno nuevo en el horario seleccionado. Valida disponibilidad del nuevo slot. Todo dentro de `@transaction.atomic`.

#### registrar_checkin(turno)

Marca el check-in del paciente registrando la hora de llegada. Solo permite check-in el día del turno. Cambia el estado a `confirmado`.

#### marcar_noshow(turno)

Marca el turno como no-show y llama a `paciente.verificar_bloqueo()` para evaluar si corresponde bloquear al paciente (RN-04).

#### marcar_atendido(turno)

Cambia el estado del turno a `atendido`. Solo permite marcar turnos con check-in previo (estado `confirmado`).

#### buscar_turnos(query, fecha, medico, especialidad, estado)

Búsqueda flexible de turnos. El parámetro `query` busca por nombre, apellido o DNI del paciente usando `icontains` (búsqueda case-insensitive). Usa `select_related` para optimizar las consultas a la base de datos.

---

## 4. Signals y automatizaciones

### Archivo: `core/signals.py`

Django permite conectar funciones a eventos del ciclo de vida de los modelos mediante signals. Usamos `post_save` del modelo `Turno`.

#### turno_post_save

Se ejecuta cada vez que se guarda un Turno:

- **Si es un turno nuevo** (`created=True`):
  - `_notificar_confirmacion()`: Crea una notificación de tipo `confirmacion` para el paciente con los datos del turno y el ID de confirmación.
  - `_crear_recordatorio()`: Crea una notificación de tipo `recordatorio` que queda pendiente hasta que el comando `enviar_recordatorios` la procese 24 horas antes del turno.

- **Si es una actualización y el estado es `cancelado`**:
  - `_notificar_cancelacion_medico()`: Crea una notificación de tipo `cancelacion` para el médico informando que le cancelaron un turno (RF-16).

#### Conexión del signal

En `core/apps.py` se importa el módulo de signals en el método `ready()`:

```python
def ready(self):
    import core.signals
```

Esto asegura que los signals se registren cuando Django inicia la aplicación.

---

## 5. Sistema de permisos

### Archivo: `core/permissions.py`

Implementa control de acceso basado en roles. Cada vista está protegida para que solo los usuarios con el rol correcto puedan acceder.

### Decoradores (para vistas basadas en funciones)

```python
@paciente_requerido          # Solo pacientes
@recepcionista_requerido     # Solo recepcionistas
@medico_requerido            # Solo médicos
@admin_requerido             # Solo administrador
@recepcion_o_admin           # Recepcionista o administrador
@rol_requerido('rol1','rol2') # Personalizable
```

**Funcionamiento:** Cada decorador verifica `request.user.rol`. Si no coincide con los roles permitidos, lanza `PermissionDenied` (error 403). Todos incluyen `@login_required` internamente, por lo que redirigen al login si el usuario no está autenticado.

### Mixins (para vistas basadas en clases)

```python
class MiVista(PacienteRequiredMixin, View):
    pass
```

Disponibles: `PacienteRequiredMixin`, `RecepcionistaRequiredMixin`, `MedicoRequiredMixin`, `AdminRequiredMixin`, `RecepcionOAdminMixin`.

Heredan de `LoginRequiredMixin` y `UserPassesTestMixin` de Django.

---

## 6. Reportes y estadísticas

### Archivo: `reportes/utils.py`

#### reporte_ocupacion_por_medico(fecha_desde, fecha_hasta)

**RF-17.** Calcula el porcentaje de ocupación de cada médico.

**Algoritmo:**
1. Para cada médico, calcula los slots totales disponibles en el rango de fechas recorriendo día por día y generando los slots según su `DisponibilidadMedica`
2. Cuenta los turnos activos (reservados, confirmados, atendidos, no-show) en ese rango
3. Calcula: `porcentaje = turnos_tomados / slots_totales * 100`

Retorna lista ordenada por porcentaje de ocupación descendente.

#### reporte_ocupacion_por_especialidad(fecha_desde, fecha_hasta)

**RF-18.** Misma lógica que el anterior pero agrupado por especialidad. Suma los slots de todos los médicos de cada especialidad.

#### reporte_ausentismo(fecha_desde, fecha_hasta, medico=None, especialidad=None)

**RF-19.** Calcula la tasa de ausentismo:

- `tasa = no_shows / total_turnos * 100`

Retorna datos globales y desgloses opcionales por médico y por especialidad. Los desgloses usan `annotate()` de Django para hacer las agregaciones en una sola consulta SQL.

#### reporte_turnos_por_canal(fecha_desde, fecha_hasta)

**RF-20.** Agrupa los turnos por canal de origen (online, teléfono, presencial) usando `values().annotate(Count)`. Calcula cantidad y porcentaje de cada canal.

---

## 7. Vistas y URLs

### authentication (URLs raíz `/`)

| URL | Vista | Método | Descripción |
|-----|-------|--------|-------------|
| `/` | `dashboard_view` | GET | Redirige según el rol del usuario |
| `/login/` | `login_view` | GET/POST | Formulario de inicio de sesión |
| `/registro/` | `registro_view` | GET/POST | Formulario de registro de paciente |
| `/logout/` | `logout_view` | GET | Cierra la sesión |

### pacientes (`/pacientes/`)

| URL | Vista | Método | RF |
|-----|-------|--------|----|
| `/pacientes/` | `mis_turnos_view` | GET | RF-06 |
| `/pacientes/buscar/` | `buscar_especialidad_view` | GET | RF-01 |
| `/pacientes/especialidad/<id>/` | `seleccionar_turno_view` | GET | RF-02 |
| `/pacientes/reservar/` | `reservar_turno_view` | POST | RF-03 |
| `/pacientes/cancelar/<id>/` | `cancelar_turno_view` | GET/POST | RF-04 |
| `/pacientes/reprogramar/<id>/` | `reprogramar_turno_view` | GET/POST | RF-05 |

### recepcion (`/recepcion/`)

| URL | Vista | Método | RF |
|-----|-------|--------|----|
| `/recepcion/` | `panel_view` | GET | — |
| `/recepcion/telefonico/` | `registrar_turno_telefonico_view` | GET/POST | RF-08 |
| `/recepcion/checkin/<id>/` | `checkin_view` | POST | RF-10 |
| `/recepcion/noshow/<id>/` | `noshow_view` | POST | RF-11 |
| `/recepcion/atendido/<id>/` | `atendido_view` | POST | — |
| `/recepcion/cancelar/<id>/` | `cancelar_turno_recepcion_view` | GET/POST | RF-09 |
| `/recepcion/buscar/` | `buscar_turnos_view` | GET | RF-12 |

### medicos (`/medicos/`)

| URL | Vista | Método | RF |
|-----|-------|--------|----|
| `/medicos/agenda/` | `agenda_view` | GET | RF-13, RF-14 |
| `/medicos/bloquear/` | `bloquear_horario_view` | GET/POST | RF-15 |
| `/medicos/bloqueos/` | `mis_bloqueos_view` | GET | RF-15 |

### reportes (`/reportes/`)

| URL | Vista | Método | RF |
|-----|-------|--------|----|
| `/reportes/` | `dashboard_view` | GET | CU-06 |
| `/reportes/ocupacion-medico/` | `ocupacion_medico_view` | GET | RF-17 |
| `/reportes/ocupacion-especialidad/` | `ocupacion_especialidad_view` | GET | RF-18 |
| `/reportes/ausentismo/` | `ausentismo_view` | GET | RF-19 |
| `/reportes/canales/` | `canales_view` | GET | RF-20 |

---

## 8. Templates

### Sistema de herencia

Todos los templates heredan de `base.html` usando `{% extends 'base.html' %}`. El template base define:

- **Navbar dinámica**: Muestra links diferentes según `user.rol`
- **Sistema de mensajes**: Muestra notificaciones de éxito/error/warning usando el framework de mensajes de Django
- **CSS completo**: Variables CSS, estilos para cards, tablas, botones, badges, formularios, barras de progreso, grillas de slots

### Etiquetas de template usadas

| Etiqueta | Uso |
|----------|-----|
| `{% extends %}` | Herencia de templates |
| `{% block content %}` | Define sección reemplazable |
| `{% csrf_token %}` | Token de seguridad en formularios |
| `{% url 'name' %}` | Genera URL por nombre |
| `{% if %}` / `{% elif %}` / `{% endif %}` | Condicionales |
| `{% for %}` / `{% endfor %}` | Bucles |
| `{{ variable }}` | Muestra valor de variable |
| `{{ var\|date:"d/m/Y" }}` | Filtro de formato de fecha |
| `{{ var\|default:"—" }}` | Valor por defecto si es vacío |
| `{{ var\|length }}` | Cantidad de elementos |
| `{{ var\|pluralize }}` | Pluralización automática |
| `{% widthratio %}` | Cálculo de porcentajes |

---

## 9. Comandos de gestión

### seed (`python manage.py seed`)

Carga datos de prueba en la base de datos:
- 6 especialidades con nombre y descripción
- 12 médicos (2 por especialidad) con usuario, matrícula y disponibilidades
- 5 pacientes con datos personales
- 1 recepcionista
- 1 administrador
- 8 turnos de ejemplo distribuidos en los próximos días

Es idempotente: si se ejecuta múltiples veces no duplica datos (usa `get_or_create`).

### procesar_noshows (`python manage.py procesar_noshows`)

Busca turnos con fecha pasada que estén en estado `reservado` o `confirmado` y no tengan check-in. Los marca como `no_show` y evalúa si el paciente debe ser bloqueado.

En producción se ejecutaría periódicamente con cron (ej: cada hora).

### enviar_recordatorios (`python manage.py enviar_recordatorios`)

Busca notificaciones de tipo `recordatorio` en estado `pendiente` cuyos turnos sean en las próximas 24 horas. Marca las notificaciones como enviadas.

La integración real con servicios de email/SMS/WhatsApp queda como extensión futura.

---

## 10. Trazabilidad con el ERS

### Requerimientos Funcionales

| RF | Descripción | Implementación |
|----|-------------|----------------|
| RF-01 | Buscar especialidades disponibles | `pacientes/views.py: buscar_especialidad_view` |
| RF-02 | Mostrar médicos y horarios libres | `core/utils.py: obtener_medicos_disponibles` + `pacientes/views.py: seleccionar_turno_view` |
| RF-03 | Reservar turno con DNI/celular | `core/utils.py: reservar_turno` + `pacientes/views.py: reservar_turno_view` |
| RF-04 | Cancelar turno con 2h de anticipación | `core/utils.py: cancelar_turno` + `pacientes/views.py: cancelar_turno_view` |
| RF-05 | Reprogramar turno | `core/utils.py: reprogramar_turno` + `pacientes/views.py: reprogramar_turno_view` |
| RF-06 | Historial de turnos | `pacientes/views.py: mis_turnos_view` |
| RF-07 | Turno para familiar | `core/utils.py: reservar_turno_familiar` + `core/models.py: FamiliarPaciente` |
| RF-08 | Registro telefónico rápido | `recepcion/views.py: registrar_turno_telefonico_view` |
| RF-09 | Cancelar/reprogramar desde recepción | `recepcion/views.py: cancelar_turno_recepcion_view` |
| RF-10 | Check-in del paciente | `core/utils.py: registrar_checkin` + `recepcion/views.py: checkin_view` |
| RF-11 | Marcar no-show | `core/utils.py: marcar_noshow` + `recepcion/views.py: noshow_view` |
| RF-12 | Buscar turnos por nombre/DNI/fecha | `core/utils.py: buscar_turnos` + `recepcion/views.py: buscar_turnos_view` |
| RF-13 | Agenda del médico en móvil | `medicos/views.py: agenda_view` (responsive) |
| RF-14 | Lista de pacientes del día | `medicos/views.py: agenda_view` |
| RF-15 | Bloquear horarios | `medicos/views.py: bloquear_horario_view` + `core/models.py: BloqueoHorario` |
| RF-16 | Notificar cancelación al médico | `core/signals.py: _notificar_cancelacion_medico` |
| RF-17 | Reporte ocupación por médico | `reportes/utils.py: reporte_ocupacion_por_medico` |
| RF-18 | Reporte ocupación por especialidad | `reportes/utils.py: reporte_ocupacion_por_especialidad` |
| RF-19 | Reporte tasa de ausentismo | `reportes/utils.py: reporte_ausentismo` |
| RF-20 | Turnos por canal | `reportes/utils.py: reporte_turnos_por_canal` |
| RF-21 | Impedir doble reserva | `core/utils.py: validar_reserva` (RN-01) |
| RF-22 | Registrar canal de origen | `core/models.py: Turno.canal` + automático en cada vista |
| RF-23 | Recordatorios 24h antes | `core/signals.py: _crear_recordatorio` + `core/management/commands/enviar_recordatorios.py` |

### Reglas de Negocio

| RN | Implementación |
|----|----------------|
| RN-01 | `core/utils.py: validar_reserva()` — query que verifica existencia de turno en mismo slot/médico |
| RN-02 | `core/utils.py: validar_reserva()` — query que verifica turnos simultáneos del paciente |
| RN-03 | `core/models.py: Turno.puede_cancelar` + `core/utils.py: cancelar_turno()` |
| RN-04 | `core/models.py: Paciente.verificar_bloqueo()` + `core/utils.py: marcar_noshow()` |
| RN-05 | Implícito: al cambiar estado a `cancelado`, el slot queda libre para nuevas reservas |
| RN-06 | `core/permissions.py: medico_requerido` en `medicos/views.py: bloquear_horario_view` |
| RN-07 | `core/signals.py: _crear_recordatorio` + `core/management/commands/enviar_recordatorios.py` |
| RN-08 | `core/utils.py: reservar_turno_familiar()` + `core/models.py: FamiliarPaciente` |

### Casos de Uso

| CU | Implementación |
|----|----------------|
| CU-01 Reservar Turno Online | Flujo: `buscar_especialidad_view` → `seleccionar_turno_view` → `reservar_turno_view` |
| CU-02 Cancelar Turno | `cancelar_turno_view` (paciente) / `cancelar_turno_recepcion_view` (recepción) |
| CU-03 Registrar Turno Telefónico | `registrar_turno_telefonico_view` con `canal=TELEFONO` |
| CU-04 Check-in y No-Show | `checkin_view` + `noshow_view` en panel de recepción |
| CU-05 Consultar Agenda Médica | `agenda_view` con navegación por día |
| CU-06 Generar Reporte | `dashboard_view` con los 4 reportes integrados |
