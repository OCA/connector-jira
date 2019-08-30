# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


def migrate(cr, version):
    cr.execute(
        """UPDATE ir_model_data
        SET
            name = 'ir_cron_jira_sync_tempo_timesheets_approval_status',
        WHERE
            name = 'ir_cron_jira_sync_jira_tempo_status';
        """
    )
