In the configuration file, you can configure the location, enable/disable
the SSL and the webhook base url of the JIRA Backends.

Exemple of the section to put in the configuration file::

    [jira_backend.name_of_the_backend]
    uri = http://jira
    verify_ssl = 1
    odoo_webhook_base_url = http://odoo:8069
