from django import forms
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet, inlineformset_factory

from productos.models import Producto
from proveedores.models import Proveedor

from .models import Compra, DetalleCompra


class CompraForm(forms.ModelForm):
    """Formulario para registrar y modificar compras en borrador."""

    class Meta:
        model = Compra

        fields = [
            "proveedor",
            "fecha_compra",
            "tipo_comprobante",
            "numero_comprobante",
            "observaciones",
        ]

        widgets = {
            "proveedor": forms.Select(
                attrs={
                    "class": "campo-formulario",
                }
            ),
            "fecha_compra": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "class": "campo-formulario",
                    "type": "date",
                },
            ),
            "tipo_comprobante": forms.Select(
                attrs={
                    "class": "campo-formulario",
                }
            ),
            "numero_comprobante": forms.TextInput(
                attrs={
                    "class": "campo-formulario",
                    "placeholder": "Ejemplo: FAC-001",
                }
            ),
            "observaciones": forms.Textarea(
                attrs={
                    "class": "campo-formulario",
                    "rows": 4,
                    "placeholder": "Observaciones de la compra",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["proveedor"].queryset = (
            Proveedor.objects.filter(estado=True)
            .order_by("razon_social")
        )

        self.fields["proveedor"].empty_label = (
            "Seleccione un proveedor"
        )

    def clean_numero_comprobante(self):
        numero_comprobante = self.cleaned_data.get(
            "numero_comprobante",
            "",
        )

        return numero_comprobante.strip().upper()

    def clean(self):
        """
        Evita registrar dos veces el mismo comprobante
        para un proveedor.
        """

        datos = super().clean()

        proveedor = datos.get("proveedor")
        tipo_comprobante = datos.get("tipo_comprobante")

        numero_comprobante = (
            datos.get("numero_comprobante")
            or ""
        ).strip().upper()

        if (
            proveedor
            and tipo_comprobante
            and numero_comprobante
        ):
            compras_existentes = Compra.objects.filter(
                proveedor=proveedor,
                tipo_comprobante=tipo_comprobante,
                numero_comprobante__iexact=numero_comprobante,
            )

            if self.instance and self.instance.pk:
                compras_existentes = compras_existentes.exclude(
                    pk=self.instance.pk,
                )

            if compras_existentes.exists():
                self.add_error(
                    "numero_comprobante",
                    (
                        "Ya existe una compra registrada para "
                        "este proveedor con el mismo tipo y "
                        "número de comprobante."
                    ),
                )

        return datos

class DetalleCompraForm(forms.ModelForm):
    """Formulario para agregar productos a una compra."""

    class Meta:
        model = DetalleCompra

        fields = [
            "producto",
            "cantidad",
            "costo_unitario",
            "precio_venta",
        ]

        widgets = {
            "producto": forms.Select(
                attrs={
                    "class": "campo-formulario selector-producto",
                }
            ),
            "cantidad": forms.NumberInput(
                attrs={
                    "class": "campo-formulario campo-cantidad",
                    "min": "1",
                    "placeholder": "Cantidad",
                }
            ),
            "costo_unitario": forms.NumberInput(
                attrs={
                    "class": "campo-formulario campo-costo-unitario",
                    "min": "0.01",
                    "step": "0.01",
                    "placeholder": "Costo unitario",
                }
            ),
            "precio_venta": forms.NumberInput(
                attrs={
                    "class": "campo-formulario campo-precio-venta",
                    "min": "0.01",
                    "step": "0.01",
                    "placeholder": "Precio de venta",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        """Carga únicamente los productos activos."""

        super().__init__(*args, **kwargs)

        self.fields["producto"].queryset = (
            Producto.objects
            .filter(estado=True)
            .order_by(
                "nombre",
                "codigo",
            )
        )

        self.fields["producto"].empty_label = (
            "Seleccione un producto"
        )

    def clean(self):
        """Valida que el precio de venta cubra el costo de compra."""

        datos = super().clean()

        costo_unitario = datos.get("costo_unitario")
        precio_venta = datos.get("precio_venta")

        if (
            costo_unitario is not None
            and precio_venta is not None
            and precio_venta < costo_unitario
        ):
            self.add_error(
                "precio_venta",
                (
                    "El precio de venta no puede ser menor "
                    "al costo unitario."
                ),
            )

        return datos


class BaseDetalleCompraFormSet(BaseInlineFormSet):
    """Validaciones generales de los productos de una compra."""

    def clean(self):
        super().clean()

        if any(self.errors):
            return

        productos_agregados = set()
        cantidad_detalles = 0

        for formulario in self.forms:
            datos = getattr(
                formulario,
                "cleaned_data",
                {},
            )

            if not datos:
                continue

            if datos.get("DELETE"):
                continue

            producto = datos.get("producto")

            if producto is None:
                continue

            cantidad_detalles += 1

            if producto.id in productos_agregados:
                raise ValidationError(
                    (
                        f'El producto "{producto.nombre}" '
                        "fue agregado más de una vez."
                    )
                )

            productos_agregados.add(producto.id)

        if cantidad_detalles == 0:
            raise ValidationError(
                "Debe agregar al menos un producto a la compra."
            )


DetalleCompraFormSet = inlineformset_factory(
    parent_model=Compra,
    model=DetalleCompra,
    form=DetalleCompraForm,
    formset=BaseDetalleCompraFormSet,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)