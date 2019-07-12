import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo11-addons-oca-connector-jira",
    description="Meta package for oca-connector-jira Odoo addons",
    version=version,
    install_requires=[
        'odoo11-addon-connector_jira',
        'odoo11-addon-connector_jira_servicedesk',
        'odoo11-addon-connector_jira_tempo',
        'odoo11-addon-multi_step_wizard',
        'odoo11-addon-server_env_connector_jira',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
