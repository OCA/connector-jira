The tasks and worklogs are always imported from JIRA to Odoo, there
is no synchronization in the other direction.

Initial synchronizations
~~~~~~~~~~~~~~~~~~~~~~~~

You can already select the "Imports" tab in the Backend and click on "Link
users" and "Import issue types". The users will be matched either by login or by email.

Create and export a project
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Projects can be created in Odoo and exported to Jira. You can then create a
project, and use the action "Link with JIRA" and use the "Export to JIRA" action.

When you choose to export a project to JIRA, if you change the name
or the key of the project, the new values will be pushed to JIRA.

Link a project with JIRA
~~~~~~~~~~~~~~~~~~~~~~~~

If you already have a project on JIRA or prefer to create it first on JIRA,
you can link an Odoo project. Use the "Link with JIRA" action on the project
and select the "Link with JIRA" action.

This action establish the link, then changes of the name or the key on either
side are not pushed.

Issue Types on Projects
~~~~~~~~~~~~~~~~~~~~~~~

When you link a project, you have to select which issue types are synchronized.
Only tasks of the selected types will be created in Odoo.

If a JIRA worklog is added to a type of issue that is not synchronized,
will attach to the closest task following these rules:

* if a subtask, find the parent task
* if no parent task, find the epic task (only if it is on the same project)
* if no epic, attach to the project without being linked to a task

Change synchronization configuration on a project
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you want to change the configuration of a project, such as which
issue types are synchronized, you can open the "Connector" tab in
the project settings and edit the "binding" with the backend.

Synchronize tasks and worklogs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If the webhooks are active, as soon as they are created in Jira they should appear in Odoo.
If they are not active, you can open the Jira Backend and run the
synchronizations manually, or activate the Scheduled Actions to run the batch
imports. It is important to select the issue types so don't miss this step (need improvement).
