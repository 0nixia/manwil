from odoo import models, fields


class InvoiceItem(models.Model):
	_name = 'siat.invoiceitem'
	_description = 'Invoice Item data model'

	company_id = fields.Many2one(
        related='invoice_id.company_id',
        store=True,
        string='Company',
        readonly=True,
    )
	invoice_id = fields.Many2one('siat.invoice')
	product_id = fields.Many2one('product.product')
	product_code = fields.Char(size=64, required=True)
	product_name = fields.Char(size=512, required=True)
	price = fields.Float(default=0)
	quantity = fields.Float(default=1)
	subtotal = fields.Float(required=True)
	discount = fields.Float(required=True)
	total = fields.Float(required=True)
	codigo_actividad = fields.Char(size=64, required=True)
	codigo_producto_sin = fields.Integer(required=True)
	unidad_medida = fields.Integer(required=True)
	numero_seria = fields.Char(size=64, required=False, default=None)
	numero_imei = fields.Char(size=64, required=False, default=None)
	nandina = fields.Char(size=64, required=False, default=None)

	@staticmethod
	def get_unidad_medida(env, codigo_unidad_medida: int):
		from ..services.service_siat_sync import ServiceSiatSync
		service = ServiceSiatSync(env)
		return service.buscar_unidad_medida(codigo_unidad_medida)

	def get_report_description(self):
		"""Descripción del producto con sus atributos de variante, sin el [código].

		Construye el nombre directamente desde los campos ORM de la variante
		(product_tmpl_id.name + product_template_attribute_value_ids) en vez de
		parsear display_name. Fuerza es_BO porque el comprobante fiscal boliviano
		debe emitirse en español y esos campos son traducibles. Fallback al
		product_name (snapshot) si el item no tiene producto asociado.
		"""
		self.ensure_one()
		product = self.product_id
		if not product:
			return self.product_name or ''
		# El comprobante fiscal boliviano debe emitirse en español: product_tmpl_id.name
		# y los nombres de los valores de atributo son campos traducibles.
		# Aplicar es_BO SOLO si está activo en la instancia; si no, mantener
		# el lang del env actual (evita UserError 'Invalid language code'
		# en instancias donde el pack es_BO existe pero no está activado).
		if self.env['res.lang'].sudo().search_count(
			[('code', '=', 'es_BO'), ('active', '=', True)]
		):
			product = product.with_context(lang='es_BO')
		name = product.product_tmpl_id.name or ''
		variant_values = product.product_template_attribute_value_ids
		if variant_values:
			attrs = ', '.join(v.name for v in variant_values if v.name)
			if attrs:
				name = "%s (%s)" % (name, attrs)
		return name or self.product_name or ''