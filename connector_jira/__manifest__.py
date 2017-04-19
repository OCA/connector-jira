# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{'name': 'JIRA Connector',
 'version': '10.0.1.0.0',
 'author': 'Camptocamp,Odoo Community Association (OCA)',
 'license': 'AGPL-3',
 'category': 'Connector',
 'depends': ['connector',
             'project',
             'hr_timesheet',
             'queue_job',
             'web',
             ],
 'external_dependencies': {
     'python': [
         'requests',
         'jira',
         'oauthlib',
         # 'requests-oauthlib',
         # 'requests-toolbelt',
         # 'PyJWT',
         'cryptography',
      ],
 },
 'website': 'https://www.camptocamp.com',
 'data': [
     'views/jira_menus.xml',
     'wizards/jira_backend_auth_views.xml',
     'views/jira_backend_views.xml',
     'views/project_project_views.xml',
     'views/project_task_views.xml',
     'views/res_users_views.xml',
     'views/jira_issue_type_views.xml',
     'security/ir.model.access.csv',
     'data/cron.xml',
     ],
 'installable': True,
 }
