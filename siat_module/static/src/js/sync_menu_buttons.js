/** @odoo-module */
import { ListController } from "@web/views/list/list_controller";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';
import { useService } from '@web/core/utils/hooks';

export class SyncListController extends ListController {
    setup() {
        super.setup();
        this.orm = useService("orm");
    }
    async SyncList() {
        try {
            await this.orm.call(this.props.resModel, 'sync_model', [''], {});
            window.location.reload();
        } catch (error) {
            console.error('Error:', error);
        }
    }
    async SyncAllList() {
        try {
            await this.orm.call('res.config.settings', 'request_cuis', [''], {});
            window.location.reload();
        } catch (error) {
            console.error('Error:', error);
        }
    }
}
registry.category("views").add("button_in_list_sync", {
   ...listView,
   Controller: SyncListController,
   buttonTemplate: "button_sync.ListView.Buttons",
});
registry.category("views").add("button_in_tree_sync", {
   ...listView,
   Controller: SyncListController,
   buttonTemplate: "button_sync.ListView.Buttons",
});
