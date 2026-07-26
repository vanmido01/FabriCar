from django import forms
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet, inlineformset_factory

from clientes.models import Cliente
from productos.models import Producto

from .models import DetalleVenta, Venta


class VentaForm(forms.ModelForm):
    """Formulario para registrar y modificar ventas en borrador."""

    class Meta:
        model = Venta

        fields = [
            "cliente",
            "fecha_venta",
            "tipo_comprobante",
            "numero_comprobante",
            "forma_pago",
            "observaciones",
        ]

        widgets = {
            "cliente": forms.Select(
                attrs={
                    "class": "campo-formulario",
                }
            ),
            "fecha_venta": forms.DateInput(
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
                    "placeholder": "Ejemplo: VEN-001",
                }
            ),
            "forma_pago": forms.Select(
                attrs={
                    "class": "campo-formulario",
                }
            ),
            "observaciones": forms.Textarea(
                attrs={
                    "class": "campo-formulario",
                    "rows": 4,
                    "placeholder": "Observaciones de la venta",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["cliente"].queryset = (
            Cliente.objects.filter(estado=True)
            .order_by("nombre")
        )

        self.fields["cliente"].empty_label = (
            "Seleccione un cliente"
        )

    def clean_numero_comprobante(self):
        numero_comprobante = self.cleaned_data.get(
            "numero_comprobante",
            "",
        )

        return numero_comprobante.strip().upper()


class DetalleVentaForm(forms.ModelForm):
    """Formulario para agregar productos a una venta."""

    class Meta:
        model = DetalleVenta

        fields = [
            "producto",
            "cantidad",
            "precio_unitario",
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
            "precio_unitario": forms.NumberInput(
                attrs={
                    "class": "campo-formulario",
                    "min": "0.01",
                    "step": "0.01",
                    "placeholder": "Precio unitario",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["producto"].queryset = (
            Producto.objects.filter(
                estado=True,
                stock_actual__gt=0,
            )
            .order_by("nombre")
        )

        self.fields["producto"].empty_label = (
            "Seleccione un producto"
        )


class BaseDetalleVentaFormSet(BaseInlineFormSet):
    """Valida los productos incluidos en una venta."""

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
            cantidad = datos.get("cantidad")

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

            if cantidad and cantidad > producto.stock_actual:
                formulario.add_error(
                    "cantidad",
                    (
                        "La cantidad solicitada supera el stock "
                        f"disponible de {producto.stock_actual}."
                    ),
                )

        if cantidad_detalles == 0:
            raise ValidationError(
                "Debe agregar al menos un producto a la venta."
            )


DetalleVentaFormSet = inlineformset_factory(
    parent_model=Venta,
    model=DetalleVenta,
    form=DetalleVentaForm,
    formset=BaseDetalleVentaFormSet,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)