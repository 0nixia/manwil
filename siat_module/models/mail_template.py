from odoo import models


class SiatMailTemplate(models.Model):
    _inherit = 'mail.template'
    append_attachments = []

    def generate_email(self, res_ids, fields):
        res = super(SiatMailTemplate, self).generate_email(res_ids, fields)
        if self.model != 'siat.invoice':
            return res
        print('APPEND ATTACHMENTS TO EMAIL')
        for attach in SiatMailTemplate.append_attachments:
            res['attachments'].append( attach )
        return res