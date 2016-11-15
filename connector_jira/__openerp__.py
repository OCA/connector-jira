# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{'name': 'Connector Jira',
 'version': '9.0.1.0.0',
 'author': 'Camptocamp,Odoo Community Association (OCA)',
 'license': 'AGPL-3',
 'category': 'Connector',
 'depends': ['connector',
             ],
 'website': 'http://www.camptocamp.com',
 'data': [
     'views/jira_menus.xml',
     'wizards/jira_backend_auth_views.xml',
     'views/jira_backend_views.xml',
     ],
 'installable': True,
 }
