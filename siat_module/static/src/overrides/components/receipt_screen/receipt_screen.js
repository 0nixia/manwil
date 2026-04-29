/** @odoo-module **/

import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.report = useService("report");
        this.orm = useService("orm");
    },
    async printSiatTicket() {
        const order = this.currentOrder;
        const moveId = order.raw?.account_move;
        if (!moveId) {
            this.env.services.notification.add(
                "No se encontró el ID de la factura en el servidor.",
                { title: "SIAT: Error", type: "danger" }
            );
            return;
        }
        let printName = "Ticket SIAT";
        try {
            const result = await this.orm.read(
                "account.move",
                [moveId],
                ["name", "siat_invoice_id"]
            );
            if (result && result[0]) {
                const moveName = result[0].name || "";
                let invoiceNumber = "";
                if (result[0].siat_invoice_id) {
                    const invoiceId = Array.isArray(result[0].siat_invoice_id)
                        ? result[0].siat_invoice_id[0]
                        : result[0].siat_invoice_id;
                    const invoiceResult = await this.orm.read(
                        "siat.invoice",
                        [invoiceId],
                        ["invoice_number"]
                    );
                    if (invoiceResult && invoiceResult[0]) {
                        invoiceNumber = invoiceResult[0].invoice_number || "";
                    }
                }
                printName = `Factura - ${moveName} - ${invoiceNumber}`.trim().replace(/\s*-\s*$/, "");
            }
        } catch (e) {
            console.warn("SIAT: No se pudo obtener el nombre del reporte:", e);
        }
        const reportUrl = `/report/html/siat_module.siat_invoice_report_ticket/${moveId}`;
        const iframe = document.createElement("iframe");
        iframe.style.position = "fixed";
        iframe.style.top = "0";
        iframe.style.left = "0";
        iframe.style.width = "1px";
        iframe.style.height = "1px";
        iframe.style.opacity = "0";
        iframe.style.pointerEvents = "none";
        iframe.style.border = "none";
        iframe.style.zIndex = "-1";
        iframe.src = reportUrl;
        document.body.appendChild(iframe);
        iframe.addEventListener("load", () => {
            try {
                const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                const style = iframeDoc.createElement("style");
                style.textContent = `
                    @media print {
                        .o_report_footer,
                        #footer,
                        .footer { display: none !important; }
                        @page { margin-bottom: 5mm; }
                    }
                `;
                iframeDoc.head.appendChild(style);
                const images = iframeDoc.querySelectorAll("img");
                const imagePromises = Array.from(images).map((img) => {
                    if (img.complete) return Promise.resolve();
                    return new Promise((resolve) => {
                        img.addEventListener("load", resolve);
                        img.addEventListener("error", resolve);
                    });
                });
                Promise.all(imagePromises).then(() => {
                    const originalTitle = document.title;
                    document.title = printName;
                    iframe.contentWindow.focus();
                    iframe.contentWindow.print();
                    iframe.contentWindow.addEventListener("afterprint", () => {
                        document.title = originalTitle;
                    });
                    setTimeout(() => {
                        document.title = originalTitle;
                        if (document.body.contains(iframe)) {
                            document.body.removeChild(iframe);
                        }
                    }, 5000);
                });
            } catch (e) {
                console.error("SIAT print error:", e);
                if (document.body.contains(iframe)) {
                    document.body.removeChild(iframe);
                }
            }
        });
    },
});