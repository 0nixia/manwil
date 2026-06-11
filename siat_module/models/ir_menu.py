from odoo import models, api, tools


class Menu(models.Model):
  _inherit = 'ir.ui.menu'

  @api.model
  @tools.ormcache('frozenset(self.env.user.groups_id.ids)', 'debug')
  def _visible_menu_ids(self, debug=False):
    menus = super(Menu, self)._visible_menu_ids(debug)
    config = self.env['ir.config_parameter'].sudo().get_param('siat_config.mode_siat')
    if config != '1':
      menu_item_id = self.env.ref('siat_module.pending_invoices').id
      menus.discard(menu_item_id)
    return menus