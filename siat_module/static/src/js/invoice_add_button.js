/** @odoo-module */
import { ListController } from "@web/views/list/list_controller";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';
export class InvoiceListController extends ListController {
    setup() {
        super.setup();
    }
    NewInvoice() {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'siat.invoicer',
            name:'Nueva Factura',
            view_mode: 'form',
            view_type: 'form',
            views: [[false, 'form']],
            target: 'current',
            res_id: false,
        });
    }
    VoidInvoice() {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: 'siat.invoice.cancellation.by.cuf',
            name: 'Anular Factura',
            view_mode: 'form',
            view_type: 'form',
            views: [[false, 'form']],
            target: 'new',
        });
    }
}
registry.category("views").add("button_in_list", {
    ...listView,
    Controller: InvoiceListController,
    buttonTemplate: "button_invoice.ListView.Buttons",
});
