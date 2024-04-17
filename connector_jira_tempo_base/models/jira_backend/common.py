from odoo import fields, models


class JiraBackend(models.Model):
    _inherit = "jira.backend"

    webservice_backend_id = fields.Many2one("webservice.backend")
