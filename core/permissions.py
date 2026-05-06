from functools import wraps
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied


# ---------------------------------------------------------------------------
# Decoradores para vistas basadas en funciones
# ---------------------------------------------------------------------------

def rol_requerido(*roles):
    """
    Decorador que restringe el acceso a usuarios con los roles indicados.
    Uso: @rol_requerido('medico', 'admin')
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if request.user.rol not in roles:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def paciente_requerido(view_func):
    return rol_requerido('paciente')(view_func)


def recepcionista_requerido(view_func):
    return rol_requerido('recepcionista')(view_func)


def medico_requerido(view_func):
    return rol_requerido('medico')(view_func)


def admin_requerido(view_func):
    return rol_requerido('admin')(view_func)


def recepcion_o_admin(view_func):
    return rol_requerido('recepcionista', 'admin')(view_func)


# ---------------------------------------------------------------------------
# Mixins para vistas basadas en clases
# ---------------------------------------------------------------------------

class RolRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin base. Subclases definen roles_permitidos.
    Uso: class MiVista(PacienteRequiredMixin, View): ...
    """
    roles_permitidos = []

    def test_func(self):
        return self.request.user.rol in self.roles_permitidos


class PacienteRequiredMixin(RolRequiredMixin):
    roles_permitidos = ['paciente']


class RecepcionistaRequiredMixin(RolRequiredMixin):
    roles_permitidos = ['recepcionista']


class MedicoRequiredMixin(RolRequiredMixin):
    roles_permitidos = ['medico']


class AdminRequiredMixin(RolRequiredMixin):
    roles_permitidos = ['admin']


class RecepcionOAdminMixin(RolRequiredMixin):
    roles_permitidos = ['recepcionista', 'admin']
