Setup
~~~~~

A new button is added on the JIRA backend, to import the organizations
of JIRA. Before, be sure to use the button "Configure Organization Link"
in the "Advanced Configuration" tab.


Features
~~~~~~~~

Organizations
~~~~~~~~~~~~~

On Service Desk, you can share projects with Organizations.
You may want to use different Odoo projects according to the
organizations. This is what this extension allows.

Example:

* You have one Service Desk project named "Earth Project" with key EARTH
* On JIRA SD You share this project with organizations Themis and Rhea
* However on Odoo, you want to track the hours differently for Themis and Rhea

Steps on Odoo:

* Create a Themis project, use the "Link with JIRA" action with the key EARTH
* When you hit Next, the organization(s) you want to link must be set
* Repeat with another project for Rhea

If the project binding for the synchronization already exists, you can still edit it in the settings of the project and change the organizations.

When a task or worklog is imported, it will search for a project having
exactly the same set of organizations than the one of the task. If no
project with the same set is found and you have a project configured
without organization, the task will be linked to it.

This means that, on Odoo, you can have shared project altogether with dedicated
ones, while you only have one project on JIRA.

* Tasks with org "Themis" will be attached to this project
* Tasks with org "Rhea" will be attached to this project
* Tasks with orgs "Themis" and "Rhea" will be attached to another project "Themis and Rhea"
* The rest of the tasks will be attached to a fourth project (configured without organizations)
