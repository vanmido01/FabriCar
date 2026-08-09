from decimal import Decimal

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
            "tipo_cliente",
            "cliente",
            "nombre_cliente_ocasional",
            "documento_cliente_ocasional",
            "telefono_cliente_ocasional",
            "fecha_venta",
            "tipo_comprobante",
            "numero_comprobante",
            "forma_pago",
            "fecha_vencimiento_credito",
            "monto_pago_inicial",
            "metodo_pago_inicial",
            "referencia_pago_inicial",
            "observaciones",
        ]

        widgets = {
            "tipo_cliente": forms.Select(
                attrs={
                    "class": (
                        "campo-formulario "
                        "selector-tipo-cliente"
                    ),
                }
            ),
            "cliente": forms.Select(
                attrs={
                    "class": (
                        "campo-formulario "
                        "selector-cliente-registrado"
                    ),
                }
            ),
            "nombre_cliente_ocasional": forms.TextInput(
                attrs={
                    "class": "campo-formulario",
                    "placeholder": (
                        "Ejemplo: Consumidor final"
                    ),
                }
            ),
            "documento_cliente_ocasional": forms.TextInput(
                attrs={
                    "class": "campo-formulario",
                    "placeholder": (
                        "NIT o C.I. opcional"
                    ),
                }
            ),
            "telefono_cliente_ocasional": forms.TextInput(
                attrs={
                    "class": "campo-formulario",
                    "placeholder": "Teléfono opcional",
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
                    "placeholder": (
                        "Factura, recibo u otro número externo"
                    ),
                }
            ),
            "forma_pago": forms.Select(
                attrs={
                    "class": (
                        "campo-formulario "
                        "selector-forma-pago"
                    ),
                }
            ),

            "fecha_vencimiento_credito": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "class": (
                        "campo-formulario "
                        "campo-condicion-credito"
                    ),
                    "type": "date",
                },
            ),

            "monto_pago_inicial": forms.NumberInput(
                attrs={
                    "class": (
                        "campo-formulario "
                        "campo-condicion-credito"
                    ),
                    "min": "0",
                    "step": "0.01",
                    "placeholder": "0.00",
                }
            ),

            "metodo_pago_inicial": forms.Select(
                attrs={
                    "class": (
                        "campo-formulario "
                        "campo-condicion-credito"
                    ),
                }
            ),

            "referencia_pago_inicial": forms.TextInput(
                attrs={
                    "class": (
                        "campo-formulario "
                        "campo-condicion-credito"
                    ),
                    "placeholder": (
                        "Número de transferencia, depósito "
                        "u otra referencia"
                    ),
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

        labels = {
            "tipo_cliente": "Tipo de cliente",
            "cliente": "Cliente registrado",
            "nombre_cliente_ocasional": (
                "Nombre del cliente ocasional"
            ),
            "documento_cliente_ocasional": (
                "NIT o C.I. del cliente ocasional"
            ),
            "telefono_cliente_ocasional": (
                "Teléfono del cliente ocasional"
            ),
            "numero_comprobante": (
                "Número de factura o comprobante externo"
            ),
            "fecha_vencimiento_credito": (
                "Fecha de vencimiento"
            ),

            "monto_pago_inicial": (
                "Pago inicial"
            ),

            "metodo_pago_inicial": (
                "Método del pago inicial"
            ),

            "referencia_pago_inicial": (
                "Referencia del pago inicial"
            ),           
        }

        help_texts = {
            "numero_comprobante": (
                "Campo opcional. Regístrelo solamente cuando "
                "exista una factura, recibo u otro comprobante externo."
            ),
            "fecha_vencimiento_credito": (
                "Obligatoria cuando la forma de pago sea Crédito."
            ),

            "monto_pago_inicial": (
                "Opcional. Escriba 0 si no existe un pago inicial."
            ),

            "metodo_pago_inicial": (
                "Obligatorio solamente cuando el pago inicial "
                "sea mayor a cero."
            ),

            "referencia_pago_inicial": (
                "Opcional para pagos en efectivo. Puede registrar "
                "el número de transferencia, QR o depósito."
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["cliente"].queryset = (
            Cliente.objects
            .filter(estado=True)
            .order_by("nombre")
        )

        self.fields["cliente"].empty_label = (
            "Seleccione un cliente registrado"
        )

        self.fields["cliente"].required = False

        self.fields[
            "nombre_cliente_ocasional"
        ].required = False

        self.fields[
            "documento_cliente_ocasional"
        ].required = False

        self.fields[
            "telefono_cliente_ocasional"
        ].required = False

        self.fields[
            "numero_comprobante"
        ].required = False
        self.fields[
            "fecha_vencimiento_credito"
        ].required = False

        self.fields[
            "monto_pago_inicial"
        ].required = False

        self.fields[
            "metodo_pago_inicial"
        ].required = False

        self.fields[
            "referencia_pago_inicial"
        ].required = False

        self.fields[
            "metodo_pago_inicial"
        ].choices = [
            (
                "",
                "Seleccione un método",
            ),
            *Venta.MetodoPagoInicial.choices,
        ]

        if not self.instance.pk:
            self.fields[
                "monto_pago_inicial"
            ].initial = Decimal("0.00")

    def clean_numero_comprobante(self):
        """Normaliza el número externo cuando fue registrado."""

        numero_comprobante = self.cleaned_data.get(
            "numero_comprobante",
            "",
        )

        return (
            numero_comprobante
            or ""
        ).strip().upper()

    def clean(self):
        """
        Valida el tipo de cliente, la forma de pago
        y las condiciones de una venta a crédito.
        """

        datos = super().clean()

        tipo_cliente = datos.get(
            "tipo_cliente"
        )

        cliente = datos.get(
            "cliente"
        )

        fecha_venta = datos.get(
            "fecha_venta"
        )

        forma_pago = datos.get(
            "forma_pago"
        )

        nombre_ocasional = (
            datos.get(
                "nombre_cliente_ocasional"
            )
            or ""
        ).strip()

        documento_ocasional = (
            datos.get(
                "documento_cliente_ocasional"
            )
            or ""
        ).strip().upper()

        telefono_ocasional = (
            datos.get(
                "telefono_cliente_ocasional"
            )
            or ""
        ).strip()

        fecha_vencimiento = datos.get(
            "fecha_vencimiento_credito"
        )

        monto_pago_inicial = (
            datos.get(
                "monto_pago_inicial"
            )
            or Decimal("0.00")
        )

        metodo_pago_inicial = (
            datos.get(
                "metodo_pago_inicial"
            )
            or ""
        ).strip().upper()

        referencia_pago_inicial = (
            datos.get(
                "referencia_pago_inicial"
            )
            or ""
        ).strip().upper()

        # -----------------------------------------------------
        # Cliente registrado u ocasional
        # -----------------------------------------------------

        if (
            tipo_cliente
            == Venta.TipoCliente.REGISTRADO
        ):
            if cliente is None:
                self.add_error(
                    "cliente",
                    (
                        "Debe seleccionar un cliente "
                        "registrado."
                    ),
                )

            datos[
                "nombre_cliente_ocasional"
            ] = ""

            datos[
                "documento_cliente_ocasional"
            ] = ""

            datos[
                "telefono_cliente_ocasional"
            ] = ""

        elif (
            tipo_cliente
            == Venta.TipoCliente.OCASIONAL
        ):
            datos["cliente"] = None

            datos[
                "nombre_cliente_ocasional"
            ] = (
                nombre_ocasional
                or "Consumidor final"
            )

            datos[
                "documento_cliente_ocasional"
            ] = documento_ocasional

            datos[
                "telefono_cliente_ocasional"
            ] = telefono_ocasional

            if (
                forma_pago
                == Venta.FormaPago.CREDITO
            ):
                self.add_error(
                    "forma_pago",
                    (
                        "Una venta a crédito requiere "
                        "un cliente registrado."
                    ),
                )

        # -----------------------------------------------------
        # Condiciones del crédito
        # -----------------------------------------------------

        if (
            forma_pago
            == Venta.FormaPago.CREDITO
        ):
            if fecha_vencimiento is None:
                self.add_error(
                    "fecha_vencimiento_credito",
                    (
                        "Debe registrar la fecha de "
                        "vencimiento del crédito."
                    ),
                )

            elif (
                fecha_venta
                and fecha_vencimiento < fecha_venta
            ):
                self.add_error(
                    "fecha_vencimiento_credito",
                    (
                        "La fecha de vencimiento no puede "
                        "ser anterior a la fecha de venta."
                    ),
                )

            if monto_pago_inicial < Decimal("0.00"):
                self.add_error(
                    "monto_pago_inicial",
                    (
                        "El pago inicial no puede "
                        "ser negativo."
                    ),
                )

            if (
                monto_pago_inicial
                > Decimal("0.00")
                and not metodo_pago_inicial
            ):
                self.add_error(
                    "metodo_pago_inicial",
                    (
                        "Debe seleccionar el método "
                        "del pago inicial."
                    ),
                )

            if monto_pago_inicial == Decimal("0.00"):
                datos[
                    "metodo_pago_inicial"
                ] = ""

                datos[
                    "referencia_pago_inicial"
                ] = ""

            else:
                datos[
                    "metodo_pago_inicial"
                ] = metodo_pago_inicial

                datos[
                    "referencia_pago_inicial"
                ] = referencia_pago_inicial

            datos[
                "monto_pago_inicial"
            ] = monto_pago_inicial

        else:
            # Estos valores no deben conservarse cuando
            # la venta no sea a crédito.
            datos[
                "fecha_vencimiento_credito"
            ] = None

            datos[
                "monto_pago_inicial"
            ] = Decimal("0.00")

            datos[
                "metodo_pago_inicial"
            ] = ""

            datos[
                "referencia_pago_inicial"
            ] = ""

        return datos


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
                    "class": (
                        "selector-producto "
                        "selector-producto-oculto"
                    ),
                }
            ),
            "cantidad": forms.NumberInput(
                attrs={
                    "class": (
                        "campo-formulario "
                        "campo-cantidad"
                    ),
                    "min": "1",
                    "placeholder": "Cantidad",
                }
            ),
            "precio_unitario": forms.NumberInput(
                attrs={
                    "class": (
                        "campo-formulario "
                        "campo-precio-unitario"
                    ),
                    "min": "0.01",
                    "step": "0.01",
                    "placeholder": "Precio unitario",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        """
        Carga únicamente el producto actualmente seleccionado.

        Los demás productos se buscarán mediante AJAX para evitar
        cargar cientos o miles de opciones en cada fila.
        """

        super().__init__(*args, **kwargs)

        productos_ids = set()

        # Producto existente cuando se modifica una venta.
        if (
            self.instance
            and self.instance.pk
            and self.instance.producto_id
        ):
            productos_ids.add(
                self.instance.producto_id
            )

        # Producto enviado por POST si el formulario vuelve
        # a mostrarse debido a un error de validación.
        nombre_campo_producto = self.add_prefix(
            "producto"
        )

        producto_enviado = self.data.get(
            nombre_campo_producto
        )

        if producto_enviado:
            try:
                productos_ids.add(
                    int(producto_enviado)
                )
            except (TypeError, ValueError):
                pass

        self.fields["producto"].queryset = (
            Producto.objects
            .filter(
                estado=True,
                id__in=productos_ids,
            )
            .order_by(
                "codigo",
                "nombre",
            )
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