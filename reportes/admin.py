from django.contrib import admin

from .models import ConfiguracionReportes


@admin.register(ConfiguracionReportes)
class ConfiguracionReportesAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "logo",
        "fecha_actualizacion",
    )

    readonly_fields = (
        "fecha_actualizacion",
    )

    def es_administrador(self, request):
        usuario = request.user

        if usuario.is_superuser:
            return True

        return usuario.groups.filter(
            name="Administrador"
        ).exists()

    def has_module_permission(self, request):
        return self.es_administrador(request)

    def has_view_permission(
        self,
        request,
        obj=None,
    ):
        return self.es_administrador(request)

    def has_change_permission(
        self,
        request,
        obj=None,
    ):
        return self.es_administrador(request)

    def has_add_permission(self, request):
        if not self.es_administrador(request):
            return False

        if ConfiguracionReportes.objects.exists():
            return False

        return True

    def has_delete_permission(
        self,
        request,
        obj=None,
    ):
        return False