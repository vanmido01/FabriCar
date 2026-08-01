def roles_usuario(request):
    """
    Proporciona a todas las plantillas información
    sobre el rol del usuario autenticado.
    """

    usuario = request.user

    if not usuario.is_authenticated:
        return {
            "es_administrador": False,
            "es_empleado": False,
            "es_cliente": False,
        }

    es_administrador = (
        usuario.is_superuser
        or usuario.groups.filter(
            name="Administrador"
        ).exists()
    )

    es_empleado = usuario.groups.filter(
        name="Empleado"
    ).exists()

    es_cliente = usuario.groups.filter(
        name="Cliente"
    ).exists()

    return {
        "es_administrador": es_administrador,
        "es_empleado": es_empleado,
        "es_cliente": es_cliente,
    }