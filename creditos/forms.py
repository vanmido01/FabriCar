from django import forms
from django.core.exceptions import ValidationError

from .models import Credito, PagoCredito


class CreditoForm(forms.ModelForm):
    """Permite modificar las condiciones de un crédito."""

    class Meta:
        model = Credito

        fields = [
            "fecha_vencimiento",
            "observaciones",
        ]

        widgets = {
            "fecha_vencimiento": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "class": "campo-formulario",
                    "type": "date",
                },
            ),
            "observaciones": forms.Textarea(
                attrs={
                    "class": "campo-formulario",
                    "rows": 4,
                    "placeholder": (
                        "Condiciones u observaciones del crédito"
                    ),
                }
            ),
        }

    def clean_fecha_vencimiento(self):
        fecha_vencimiento = self.cleaned_data[
            "fecha_vencimiento"
        ]

        if (
            self.instance
            and self.instance.fecha_inicio
            and fecha_vencimiento
            < self.instance.fecha_inicio
        ):
            raise ValidationError(
                "La fecha de vencimiento no puede ser "
                "anterior a la fecha de inicio."
            )

        return fecha_vencimiento


class PagoCreditoForm(forms.ModelForm):
    """Formulario para registrar pagos de una cuenta por cobrar."""

    class Meta:
        model = PagoCredito

        fields = [
            "fecha_pago",
            "monto",
            "metodo_pago",
            "referencia",
            "observaciones",
        ]

        widgets = {
            "fecha_pago": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "class": "campo-formulario",
                    "type": "date",
                },
            ),
            "monto": forms.NumberInput(
                attrs={
                    "class": "campo-formulario",
                    "min": "0.01",
                    "step": "0.01",
                    "placeholder": "Monto pagado",
                }
            ),
            "metodo_pago": forms.Select(
                attrs={
                    "class": "campo-formulario",
                }
            ),
            "referencia": forms.TextInput(
                attrs={
                    "class": "campo-formulario",
                    "placeholder": (
                        "Número de transferencia, depósito u otra referencia"
                    ),
                }
            ),
            "observaciones": forms.Textarea(
                attrs={
                    "class": "campo-formulario",
                    "rows": 4,
                    "placeholder": "Observaciones del pago",
                }
            ),
        }

    def __init__(self, *args, credito=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.credito = credito

        if credito is not None:
            self.fields["monto"].widget.attrs[
                "max"
            ] = credito.saldo_pendiente

    def clean_monto(self):
        monto = self.cleaned_data["monto"]

        if self.credito is None:
            return monto

        if self.credito.estado == Credito.EstadoCredito.ANULADO:
            raise ValidationError(
                "No se pueden registrar pagos en un crédito anulado."
            )

        if self.credito.estado == Credito.EstadoCredito.PAGADO:
            raise ValidationError(
                "El crédito ya se encuentra completamente pagado."
            )

        if monto > self.credito.saldo_pendiente:
            raise ValidationError(
                "El monto no puede superar el saldo pendiente "
                f"de Bs {self.credito.saldo_pendiente}."
            )

        return monto