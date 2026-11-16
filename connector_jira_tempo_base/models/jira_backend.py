from odoo import fields, models


class JiraBackend(models.Model):
    _inherit = "jira.backend"

    tempo_ws_backend_id = fields.Many2one("webservice.backend")
