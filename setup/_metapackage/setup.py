import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo13-addons-oca-connector-jira",
    description="Meta package for oca-connector-jira Odoo addons",
    version=version,
    install_requires=[
        'odoo13-addon-connector_jira',
        'odoo13-addon-connector_jira_servicedesk',
        'odoo13-addon-connector_jira_tempo',
        'odoo13-addon-connector_jira_tempo_base',
        'odoo13-addon-server_env_connector_jira',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 13.0',
    ]
)
