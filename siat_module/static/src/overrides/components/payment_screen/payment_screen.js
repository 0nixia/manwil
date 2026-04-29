/** @odoo-module */

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { serializeDateTime } from "@web/core/l10n/dates";
import { ConnectionLostError, RPCError } from "@web/core/network/rpc";
import { handleRPCError } from "@point_of_sale/app/errors/error_handlers";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.report = useService("report");
    },
    toggleIsToInvoiceSiat() {
        this.currentOrder.set_to_invoice_siat(!this.currentOrder.is_to_invoice_siat());
    },
    toggleIsToInvoice() {
        super.toggleIsToInvoice();
        this.currentOrder.set_to_invoice_siat(false);
    },
    async _finalizeValidation() {
        const isSiat = this.currentOrder.is_to_invoice_siat?.() || false;
        const isInvoice = this.currentOrder.is_to_invoice?.() || false;
        if (this.currentOrder.is_paid_with_cash() || this.currentOrder.get_change()) {
            this.hardwareProxy.openCashbox();
        }
        this.currentOrder.date_order = serializeDateTime(luxon.DateTime.now());
        for (const line of this.paymentLines) {
            if (!line.amount === 0) {
                this.currentOrder.remove_paymentline(line);
            }
        }
        this.pos.addPendingOrder([this.currentOrder.id]);
        this.currentOrder.state = "paid";
        this.env.services.ui.block();
        let syncOrderResult;
        try {
            syncOrderResult = await this.pos.syncAllOrders({ throw: true });
            if (!syncOrderResult) {
                return;
            }
            if (this.shouldDownloadInvoice() && isInvoice) {
                if (this.currentOrder.raw.account_move) {
                    if (isSiat) {
                        await this.report.doAction(
                            "siat_module.siat_account_invoices",
                            [this.currentOrder.raw.account_move]
                        );
                    } else {
                        await this.invoiceService.downloadPdf(
                            this.currentOrder.raw.account_move
                        );
                    }
                } else {
                    throw {
                        code: 401,
                        message: "Backend Invoice",
                        data: { order: this.currentOrder },
                    };
                }
            }
        } catch (error) {
            if (error instanceof ConnectionLostError) {
                this.afterOrderValidation();
                Promise.reject(error);
            } else if (error instanceof RPCError) {
                this.currentOrder.state = "draft";
                handleRPCError(error, this.dialog);
            } else {
                throw error;
            }
            return error;
        } finally {
            this.env.services.ui.unblock();
        }
        const postPushOrders = syncOrderResult.filter((order) => order.wait_for_push_order());
        if (postPushOrders.length > 0) {
            await this.postPushOrderResolve(postPushOrders.map((order) => order.id));
        }
        await this.afterOrderValidation(!!syncOrderResult && syncOrderResult.length > 0);
    },
});