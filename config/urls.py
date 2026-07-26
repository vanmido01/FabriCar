from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("productos/", include("productos.urls")),
    path("vehiculos/", include("vehiculos.urls")),
    path("proveedores/", include("proveedores.urls")),
    path("clientes/", include("clientes.urls")),
    path("compras/", include("compras.urls")),
    path("inventario/", include("inventario.urls")),
    path("ventas/", include("ventas.urls")),
    path("creditos/", include("creditos.urls")),
    path("reportes/", include("reportes.urls")),
    path("clasificacion/", include("clasificacion.urls")),
    path("", include("principal.urls")),
]


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )