from odoo import models, api, fields, _
from odoo.exceptions import UserError, ValidationError
from ..services.service_siat_operations import ServiceSiatOperations

NOMINATIVIDAD_LIMIT = 1000.00
SPECIAL_NITS = {"99001", "99002", "99003"}
SPECIAL_CASE_CONFIG = {
    "99001": {"fixed_name": None, "name_readonly": False},
    "99002": {"fixed_name": "Control Tributario", "name_readonly": True},
    "99003": {"fixed_name": "VENTAS MENORES DEL DÍA", "name_readonly": True},
}


class ResPartner(models.Model):
    _inherit = "res.partner"

    document_type_id = fields.Many2one(
        "siat.identity_document",
        string="Tipo de Documento",
    )
    document_type_code = fields.Char(
        related="document_type_id.code",
        store=True,
    )
    ci_complement = fields.Char(string="Complemento CI")
    is_special_siat_case = fields.Boolean(
        string="Caso Especial SIAT",
        default=False,
        help="Activa modo Caso Especial SIAT.\n99001: Extranjero/Consumidor Final\n99002: Control Tributario\n99003: Ventas Menores del Día",
    )
    siat_special_case_type = fields.Selection(
        selection=[
            ("99001", "99001 – Consumidor Final / Extranjero"),
            ("99002", "99002 – Control Tributario"),
            ("99003", "99003 – Ventas Menores del Día"),
        ],
        string="Tipo Caso Especial SIAT",
    )

    @api.depends('vat', 'document_type_id', 'is_special_siat_case', 'siat_special_case_type')
    @api.depends_context('company')
    def _compute_vat_label(self):
        for partner in self:
            if partner.is_special_siat_case and partner.siat_special_case_type:
                partner.vat_label = "NIT (Regulación SIAT)"
            elif partner.document_type_code == '5':
                partner.vat_label = "NIT"
            elif partner.document_type_code == '1':
                partner.vat_label = "Cédula de Identidad"
            elif partner.document_type_id:
                partner.vat_label = partner.document_type_id.display_name or "Nro. Documento"
            else:
                partner.vat_label = self.env.company.country_id.vat_label or _("Tax ID")

    @api.onchange("is_special_siat_case")
    def _onchange_is_special_siat_case(self):
        if self.is_special_siat_case:
            self.document_type_id = False
            self.ci_complement = False
        else:
            self.siat_special_case_type = False
            if self.vat in SPECIAL_NITS:
                self.vat = False

    @api.onchange("siat_special_case_type")
    def _onchange_siat_special_case_type(self):
        if not self.siat_special_case_type:
            return
        config = SPECIAL_CASE_CONFIG[self.siat_special_case_type]
        self.vat = self.siat_special_case_type
        if config["fixed_name"] is not None:
            self.name = config["fixed_name"]

    @api.onchange("document_type_id")
    def _onchange_document_type(self):
        if self.document_type_id and self.document_type_id.code != "1":
            self.ci_complement = False

    @staticmethod
    def _validate_special_case(effective_vals, check_stype=True, check_doc_type=True):
        is_special = effective_vals.get("is_special_siat_case", False)
        stype = effective_vals.get("siat_special_case_type", False)
        vat = effective_vals.get("vat", False)
        doc_type = effective_vals.get("document_type_id", False)
        name = effective_vals.get("name", "")
        if is_special:
            if check_stype and not stype:
                raise ValidationError(_("SIAT Special Case Type must be selected."))
            if vat and stype and vat != stype:
                raise ValidationError(
                    _("VAT must match the selected Special Case (%s).") % stype
                )
            if check_doc_type and doc_type:
                raise ValidationError(
                    _("Special SIAT Cases cannot have an Identity Document Type.")
                )
            config = SPECIAL_CASE_CONFIG.get(stype, {})
            fixed = config.get("fixed_name")
            if fixed is not None and name and name != fixed:
                raise ValidationError(
                    _("The name for Special Case '%s' must be exactly '%s'.")
                    % (stype, fixed)
                )
        else:
            doc_code = effective_vals.get("document_type_code", "")
            if doc_code == "5" and vat and not vat.isdigit():
                raise ValidationError(_("VAT must contain only numeric characters."))

    @staticmethod
    def _apply_special_case_defaults(vals):
        is_special = vals.get("is_special_siat_case")
        stype = vals.get("siat_special_case_type")
        if is_special and stype:
            config = SPECIAL_CASE_CONFIG.get(stype, {})
            vals["vat"] = stype
            vals["document_type_id"] = False
            vals["ci_complement"] = False
            if config.get("fixed_name") is not None:
                vals["name"] = config["fixed_name"]
        elif "is_special_siat_case" in vals and not vals["is_special_siat_case"]:
            vals.setdefault("siat_special_case_type", False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._apply_special_case_defaults(vals)
            effective = dict(vals)
            self._validate_special_case(effective)
        return super().create(vals_list)

    def write(self, vals):
        self._apply_special_case_defaults(vals)
        special_fields = {
            "is_special_siat_case",
            "siat_special_case_type",
            "vat",
            "document_type_id",
            "name",
        }
        touches_special = bool(special_fields & vals.keys())
        for record in self:
            if not touches_special and not record.is_special_siat_case:
                continue
            effective = {
                "is_special_siat_case": vals.get(
                    "is_special_siat_case",
                    record.is_special_siat_case,
                ),
                "siat_special_case_type": vals.get(
                    "siat_special_case_type",
                    record.siat_special_case_type,
                ),
                "vat": vals.get("vat", record.vat),
                "document_type_id": vals.get(
                    "document_type_id",
                    record.document_type_id.id,
                ),
                "document_type_code": vals.get(
                    "document_type_code",
                    record.document_type_code,
                ),
                "name": vals.get("name", record.name),
            }
            self._validate_special_case(
                effective,
                check_stype=("siat_special_case_type" in vals or "vat" in vals),
                check_doc_type=("document_type_id" in vals),
            )
        return super().write(vals)

    def nitValido(self):
        self.ensure_one()
        if self.is_special_siat_case or self.vat in SPECIAL_NITS:
            raise UserError(_("Special SIAT Cases do not require NIT verification."))
        if self.document_type_code != "5":
            raise UserError(_("SIAT verification is available only for NIT (code 5)."))
        if not self.vat:
            raise ValidationError(_("VAT/NIT cannot be empty."))
        try:
            service = ServiceSiatOperations(self.env)
            result = service.nitValido(self.vat)
            if isinstance(result, dict):
                if result.get("transaccion"):
                    return {
                        "type": "ir.actions.client",
                        "tag": "display_notification",
                        "params": {
                            "title": _("NIT Verified"),
                            "message": result.get(
                                "descripcion",
                                _("NIT successfully verified."),
                            ),
                            "type": "success",
                            "sticky": False,
                        },
                    }
                else:
                    mensajes = result.get("mensajesList", [])
                    msg = (
                        mensajes[0].get(
                            "descripcion",
                            _("Error verifying NIT."),
                        )
                        if mensajes
                        else _("Error verifying NIT.")
                    )
                    raise UserError(msg)
            raise UserError(
                _("Unexpected response from SIAT service: %s") % str(result)
            )
        except UserError:
            raise
        except Exception as e:
            raise UserError(_("Error during SIAT NIT verification: %s") % str(e))