/** @odoo-module **/

import { registry } from "@web/core/registry";
import { CharField, charField } from '@web/views/fields/char/char_field';

export class CreditCardWidget extends CharField {
    _onInput(event) {
        const value = event.target.value.replace(/\s+/g, ''); // Remove spaces
        console.log(value);
        let formattedValue;
        if (event.inputType == "deleteContentBackward" || event.inputType == "deleteContentForward") {
            if (value.length > 4 && value.length < 13) {
                const prefix = value.substring(0, 4);
                event.target.value = prefix;
            }
            return false;
        }
        if (value.length > 4) {
            const prefix = value.substring(0, 4);
            const suffix = value.length > 12 ? value.substring(value.length - 4) : '';
            const middle = '0000 0000';
            formattedValue = `${prefix} ${middle} ${suffix}`;
        } else {
            formattedValue = value;
        }
        event.target.value = formattedValue;
    }
}

CreditCardWidget.template = 'siat_module.custom_card_field';

export const cardWidget = {
    ...charField,
    component: CreditCardWidget,
};

// Register the widget with Odoo's form widget registry
registry.category("fields").add('credit_card_widget', cardWidget);
