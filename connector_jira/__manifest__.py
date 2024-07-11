# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{'name': 'JIRA Connector',
 'version': '11.0.1.0.0',
 'author': 'Camptocamp,Odoo Community Association (OCA)',
 'license': 'AGPL-3',
 'category': 'Connector',
 'depends': ['connector',
             'project',
             'hr_timesheet',
             'queue_job',
             'web',
             'web_widget_url_advanced',
             ],
 'external_dependencies': {
     'python': [
         'requests',
         'jira',
         'oauthlib',
         # these are dependencies but as they don't have the same name of
         # package / module, we can't list them here
         # 'requests-oauthlib',
         # 'requests-toolbelt',
         # 'PyJWT',
         'cryptography',
      ],
 },
 'website': 'https://github.com/camptocamp/connector-jira',
 'data': [
     'views/jira_menus.xml',
     'wizards/jira_backend_auth_views.xml',
     'views/project_link_jira_views.xml',
     'views/jira_backend_views.xml',
     'views/jira_backend_report_templates.xml',
     'views/project_project_views.xml',
     'views/project_task_views.xml',
     'views/res_users_views.xml',
     'views/jira_issue_type_views.xml',
     'views/timesheet_account_analytic_line.xml',
     'security/ir.model.access.csv',
     'data/cron.xml',
     ],
 'installable': True,
 }
