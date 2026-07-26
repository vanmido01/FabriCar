from functools import wraps

from django.core.exceptions import PermissionDenied


def rol_requerido(*roles_permitidos):
    """
    Permite acceder a una vista únicamente a los usuarios
    que pertenecen a alguno de los roles indicados.
    """

    def decorador(vista):
        @wraps(vista)
        def funcion_protegida(request, *args, **kwargs):
            usuario = request.user

            if usuario.is_superuser:
                return vista(request, *args, **kwargs)

            pertenece_al_rol = usuario.groups.filter(
                name__in=roles_permitidos
            ).exists()

            if pertenece_al_rol:
                return vista(request, *args, **kwargs)

            raise PermissionDenied

        return funcion_protegida

    return decorador