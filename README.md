# Clínica Santa Rosa - Sistema de Gestión de Turnos

Sistema web para la gestión de turnos médicos de la Clínica Santa Rosa, desarrollado con Django como proyecto académico para la cátedra de Ingeniería de Software II (Universidad de la Cuenca del Plata).

## Descripción

La Clínica Santa Rosa es una institución privada, la cual posee 12 médicos distribuidos en 6 especialidades que atiende aproximadamente 80 turnos diarios. Este sistema reemplaza el proceso manual basado en planillas de Excel, permitiendo la reserva online de turnos, gestión por recepción, consulta de agenda médica y reportes administrativos.

### Objetivos del sistema

- Reducir la carga operativa de recepción (disminuir llamadas en un 60%)
- Reducir el ausentismo de pacientes (tasa de no-show menor al 10%)
- Mejorar la ocupación de médicos
- Generar reportes consolidados para la toma de decisiones

## Especialidades

- Clínica Médica
- Pediatría
- Cardiología
- Ginecología
- Traumatología
- Dermatología

## Tecnologías

- **Backend:** Python 3.14 + Django 6.0
- **Base de datos:** SQLite (desarrollo)
- **Frontend:** Django Templates + CSS puro
- **Fuente:** Inter (Google Fonts)

## Instalación

### Requisitos previos

- Python 3.10 o superior instalado

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/Carlitoos22/clinica-santa-rosa.git
cd clinica-santa-rosa

# 2. Instalar dependencias
pip install django

# 3. Crear la base de datos
python manage.py migrate

# 4. Cargar datos de prueba
python manage.py seed

# 5. Iniciar el servidor
python manage.py runserver
```

Abrir en el navegador: **http://127.0.0.1:8000/login/**

## Usuarios de prueba

| Rol | Usuario | Contraseña |
|-----|---------|------------|
| Paciente | `rgonzalez` | `paciente123` |
| Paciente | `mdiaz` | `paciente123` |
| Paciente | `fmartinez` | `paciente123` |
| Paciente | `lsanchez` | `paciente123` |
| Paciente | `eacosta` | `paciente123` |
| Recepcionista | `recepcion1` | `recepcion123` |
| Médico | `mlopez` | `medico123` |
| Médico | `afernandez` | `medico123` |
| Médico | `lgarcia` | `medico123` |
| Administrador | `admin1` | `admin123` |

Los 12 médicos usan la misma contraseña `medico123`. Los usernames son: `mlopez`, `jramirez`, `afernandez`, `cmorales`, `lgarcia`, `rcastro`, `sparedes`, `mherrera`, `dsilva`, `vmedina`, `pruiz`, `ngomez`.

## Estructura del proyecto

```
clinica-turnos/
├── clinica/                 ← Configuración del proyecto Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── authentication/          ← Autenticación y modelo de usuario
│   ├── models.py            ← Modelo Usuario con roles
│   ├── views.py             ← Login, registro, logout, dashboard
│   ├── forms.py             ← Formularios de autenticación
│   └── admin.py
│
├── core/                    ← Aplicación principal
│   ├── models.py            ← Todos los modelos del dominio
│   ├── utils.py             ← Lógica de negocio
│   ├── signals.py           ← Notificaciones automáticas
│   ├── permissions.py       ← Decoradores y mixins de permisos
│   └── management/commands/
│       ├── seed.py          ← Carga de datos de prueba
│       ├── procesar_noshows.py
│       └── enviar_recordatorios.py
│
├── pacientes/               ← Vistas del paciente
├── recepcion/               ← Vistas de recepción
├── medicos/                 ← Vistas del médico
├── reportes/                ← Reportes y estadísticas
│   ├── utils.py             ← Lógica de reportes
│   └── views.py
│
├── templates/               ← Plantillas HTML
│   ├── base.html            ← Layout principal
│   ├── authentication/
│   ├── pacientes/
│   ├── recepcion/
│   ├── medicos/
│   └── reportes/
│
├── requirements.txt
└── manage.py
```

## Funcionalidades por rol

### Paciente
- Buscar especialidades disponibles
- Ver médicos y horarios libres
- Reservar turnos online
- Cancelar turnos (con 2 horas de anticipación)
- Reprogramar turnos
- Ver historial de turnos

### Recepcionista
- Panel con turnos del día
- Registrar turnos telefónicos (flujo rápido)
- Realizar check-in del paciente
- Marcar turnos como no-show
- Marcar turnos como atendidos
- Cancelar/reprogramar turnos a pedido
- Buscar turnos por nombre, DNI o fecha

### Médico
- Consultar agenda del día (compatible con móvil)
- Navegar entre días
- Bloquear horarios (vacaciones, congresos)
- Ver lista de bloqueos activos

### Administrador
- Dashboard con estadísticas generales
- Reporte de ocupación por médico
- Reporte de ocupación por especialidad
- Reporte de tasa de ausentismo (global y segmentado)
- Reporte de turnos por canal (online vs teléfono vs presencial)
- Filtros por rango de fechas en todos los reportes

## Reglas de negocio implementadas

| ID | Regla |
|----|-------|
| RN-01 | No se puede reservar más de un turno en el mismo horario para el mismo médico |
| RN-02 | Un paciente no puede tener dos turnos simultáneos en distintas especialidades |
| RN-03 | Las cancelaciones deben realizarse con mínimo 2 horas de anticipación; caso contrario se registran como no-show |
| RN-04 | Un paciente que acumule 3 no-shows en 60 días queda bloqueado para reservar online |
| RN-05 | Los turnos cancelados liberan el slot automáticamente |
| RN-06 | Solo el médico titular puede bloquear sus propios horarios |
| RN-07 | Los recordatorios automáticos se envían 24 horas antes del turno |
| RN-08 | Un paciente puede reservar turnos para familiares directos previa validación de vínculo |

## Comandos de gestión

```bash
# Procesar no-shows (marca turnos pasados sin check-in como ausencia)
python manage.py procesar_noshows

# Enviar recordatorios pendientes (turnos en las próximas 24 horas)
python manage.py enviar_recordatorios

# Cargar datos de prueba
python manage.py seed
```

## Equipo

- **Bonne Homero Tobías**
- **Alfaro Carlos** — Backend
- **Salazar Juan**
- **Salazar Sebastián**

## Contexto académico

- **Universidad:** Universidad de la Cuenca del Plata
- **Carrera:** Ingeniería en Sistemas de Información
- **Cátedra:** Ingeniería de Software II
- **Año:** 3° ISI COM B
- **Profesora:** Ing. Neuendorf Gladys
- **Documento base:** ERS v2.0 conforme a IEEE 830 / ISO/IEC/IEEE 29148
