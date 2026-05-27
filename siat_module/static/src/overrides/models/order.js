/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    setup(vals) {
        super.setup(vals);
        this.to_invoice_siat = vals.to_invoice_siat || false;
        if (this.uiState && this.uiState.to_invoice_siat === undefined) {
            this.uiState.to_invoice_siat = this.to_invoice_siat;
        }
    },
    set_to_invoice_siat(to_invoice) {
        this.assert_editable();
        this.to_invoice_siat = to_invoice;
        if (this.uiState) {
            this.uiState.to_invoice_siat = to_invoice;
        }
    },
    is_to_invoice_siat() {
        if (this.uiState && this.uiState.to_invoice_siat !== undefined) {
            return this.uiState.to_invoice_siat;
        }
        return this.to_invoice_siat;
    },
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        if (json) {
            json.to_invoice_siat = this.is_to_invoice_siat();
        }
        return json;
    },
});