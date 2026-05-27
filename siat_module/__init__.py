# -*- coding: utf-8 -*-
import logging
from . import models

_logger = logging.getLogger(__name__)

def pre_uninstall_hook(env):
    _logger.info("Desinstalando módulo SIAT")
    env['ir.config_parameter'].search([
        ('key', 'ilike', 'siat%')
    ]).unlink()