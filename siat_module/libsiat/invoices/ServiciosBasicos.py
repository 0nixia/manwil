from .CompraVenta import CompraVenta
from .InvoiceHeaderServiciosBasicos import InvoiceHeaderServiciosBasicos
from .invoicedetail import InvoiceDetail


class ServiciosBasicos(CompraVenta):

    def __init__(self):
        super().__init__()
        self._classAlias = 'facturaComputarizadaServicioBasico'
        self._namespaces['xsi:noNamespaceSchemaLocation'] = self._classAlias + ".xsd"
        self.cabecera = InvoiceHeaderServiciosBasicos()

    def validate(self):
        super().validate()

    def check_amounts(self):
        self.cabecera.check_amounts()
        subtotal = self.get_subtotal()
        subtotal -= self.cabecera.descuentoAdicional

        self.cabecera.montoTotal = subtotal
        self.cabecera.montoTotalMoneda = self.cabecera.montoTotal * self.cabecera.tipoCambio
        self.cabecera.montoTotalSujetoIva = self.get_amount_iva()

        self.cabecera.detalleAjusteNoSujetoIva = self.format_details(self.cabecera.detalleAjusteNoSujetoIva)
        self.cabecera.detalleAjusteSujetoIva = self.format_details(self.cabecera.detalleAjusteSujetoIva)
        self.cabecera.detalleOtrosPagosNoSujetoIva = self.format_details(self.cabecera.detalleOtrosPagosNoSujetoIva)

    def instanceDetail(self):

        detail = InvoiceDetail()
        detail.skipProperty('numeroSerie')
        detail.skipProperty('numeroImei')

        return detail

    def get_subtotal(self):
        subtotal = 0;
        for d in self.detalle:
            subtotal += d.subTotal

        subtotal += self.get_amount_tasas()
        subtotal += self.cabecera.ajusteSujetoIva
        subtotal += self.cabecera.otrosPagosNoSujetoIva

        return subtotal

    def get_amount_iva(self):
        amount = self.get_subtotal()
        amount -= self.cabecera.tasaAseo
        amount -= self.cabecera.tasaAlumbrado
        amount -= self.cabecera.otrasTasas
        amount -= self.cabecera.otrosPagosNoSujetoIva

        return amount

    def get_amount_tasas(self):
        total = self.cabecera.tasaAseo
        total += self.cabecera.tasaAlumbrado
        total += self.cabecera.otrasTasas

        return total

    def get_pay_amount(self):
        return self.get_subtotal() - self.cabecera.descuentoAdicional - self.cabecera.ajusteNoSujetoIva