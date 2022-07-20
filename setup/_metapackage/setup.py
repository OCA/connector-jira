import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo-addons-oca-connector-jira",
    description="Meta package for oca-connector-jira Odoo addons",
    version=version,
    install_requires=[
        'odoo-addon-connector_jira>=15.0dev,<15.1dev',
        'odoo-addon-connector_jira_servicedesk>=15.0dev,<15.1dev',
        'odoo-addon-server_env_connector_jira>=15.0dev,<15.1dev',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 15.0',
    ]
)
