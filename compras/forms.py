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


class DetalleCompraForm(forms.ModelForm):
    """Formulario para agregar productos a una compra."""

    class Meta:
        model = DetalleCompra

        fields = [
            "producto",
            "cantidad",
            "costo_unitario",
        ]

        widgets = {
            "producto": forms.Select(
                attrs={
                    "class": "campo-formulario",
                }
            ),
            "cantidad": forms.NumberInput(
                attrs={
                    "class": "campo-formulario",
                    "min": "1",
                    "placeholder": "Cantidad",
                }
            ),
            "costo_unitario": forms.NumberInput(
                attrs={
                    "class": "campo-formulario",
                    "min": "0.01",
                    "step": "0.01",
                    "placeholder": "Costo unitario",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["producto"].queryset = (
            Producto.objects.filter(estado=True)
            .order_by("nombre")
        )

        self.fields["producto"].empty_label = (
            "Seleccione un producto"
        )


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