# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models, api
from datetime import datetime, timedelta
from collections import defaultdict
import logging

_logger = logging.getLogger(__name__)


def get_past_week_1st_day():
    today = datetime.today()
    date = today - timedelta(
        days=today.weekday() % 7
    ) - timedelta(weeks=1)
    return date.strftime('%Y-%m-%d')


class JiraBackend(models.Model):
    _inherit = 'jira.backend'

    # TODO: shall we sync Odoo groups w/ JIRA groups?
    # shall we sync JIRA groups only as independent records
    # and replace this field w/ a m2o?
    # ATM (2019-05-08) we don't have time and we don't care.
    # We just need to pull all the TS statuses
    # but we need the ID of a JIRA groups containing ALL employees.
    jira_company_team_id = fields.Integer(
        help="This field contains the ID of a company wide group on JIRA. "
             "Its main usage is to fetch tempo statuses for ALL employees."
    )
    validate_approved_ts = fields.Boolean(
        help="If this flag is ON, once the status is sync'ed from Jira, "
             "all approved timesheets will be validated on Odoo as well."
    )

    @api.multi
    def _scheduler_sync_jira_tempo_status(self, period_start=None):
        """Synchronize JIRA Tempo timesheet status on Odoo TS lines.

        Look up for previous week timesheets and update Odoo status.
        If `period_start` is given, it will be used as look up date.

        :param period_start: custom date (server format) for the beginning
        of the period
        """
        if period_start is None:
            # NOTE: it seems that the preciseness of this date
            # is not really important.
            # If you don't pass the very begin date of the period
            # but a date in the middle, the api will give you back
            # the right period range matching that date.
            # Still, we want to put clear that we want to retrieve
            # the past week period.
            period_start = get_past_week_1st_day()
        for backend in self:
            backend._sync_jira_tempo_status(period_start)

    def _sync_jira_tempo_status(self, period_start):
        """Find users and TS lines and update tempo status."""
        team_id = self.jira_company_team_id
        with self.work_on('jira.account.analytic.line') as work:
            importer = work.component(usage='backend.adapter')
            result = importer.tempo_read_status_by_team(team_id, period_start)
            user_binder = importer.binder_for('jira.res.users')
        # Pick the date range from the Tempo period.
        # In this way we make sure we affect only the dates we want.
        date_from = result['period']['dateFrom']
        date_to = result['period']['dateTo']
        approvals = result.get('approvals', [])
        mapping = defaultdict(list)
        for entry in approvals:
            user_data = entry['user']
            try:
                user = user_binder.to_internal(user_data['key'], unwrap=True)
            except ValueError:
                _logger.error('User %(key)s not found' % user_data)
                continue
            mapping[entry['status']].append(user.id)
        for state, user_ids in mapping.items():
            self._update_ts_line_status(date_from, date_to, state, user_ids)

    def _update_ts_line_status(self, date_from, date_to, state, user_ids):
        lines = self._get_ts_lines(date_from, date_to, user_ids)
        lines.mapped('jira_bind_ids').write({
            'jira_tempo_status': state,
        })
        self._validate_ts(date_from, date_to, state, user_ids)

    def _get_ts_lines_domain(self, date_from, date_to, user_ids):
        domain = [
            # TODO: any better filter here?
            # `is_timesheet` is not available since we don't use ts_grid
            # But `is_timesheet` is a computed field with value:
            # project_id setted
            ('project_id', '!=', False),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('user_id', 'in', user_ids)
        ]
        return domain

    def _get_ts_lines(self, date_from, date_to, user_ids):
        ts_line_model = self.env['account.analytic.line']
        domain = self._get_ts_lines_domain(date_from, date_to, user_ids)
        return ts_line_model.search(domain)

    def _validate_ts(self, date_from, date_to, state, user_ids):
        # hook here and do what you want depending on the state
        # eg: if self.validate_approved_ts and state == 'approved'
        pass
