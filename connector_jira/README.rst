JIRA Connector
==============

Dependencies
------------

You need the following Python packages

* requests
* jira
* oauthlib
* requests-oauthlib
* requests-toolbelt
* PyJWT
* cryptography

Setup
-----

Once the addon is installed, follow these steps:

Backend
^^^^^^^

1. Open the menu Connectors > Jira > Backends
2. Create a new Jira Backend

   * Put the name you want
   * Set the URL of your Jira, like https://jira.example.com
   * You can also select the company where records will be created and the
     default project template used when Odoo will create the projects in Jira

3. Save and continue with the Authentication

Authentication of Backend
^^^^^^^^^^^^^^^^^^^^^^^^^

1. On the created backend, click on the Authenticate button, a popup with keys
   will appear, keep these open in a tab
2. Open Jira and go to System > Applications > Application links
3. Enter the name of the application, example: odoo, and click on "Create new link"
4. In the popup, set the URL where JIRA can reach Odoo. Jira might complain and
   reopen the popup, confirm it again and a new popup appears
5. In the new popup, do not set anything in the fields and click on Continue
6. The link should be created now, edit it with the pen on the right
7. Open the Incoming Authentication panel, be warned that it may take some time
   to load
8. Copy-paste the consumer key and public key from Odoo to the Jira link's
   Incoming Authentication. Set a consumer name (e.g. odoo) and leave the
   consumer callback url and 2 legged auth blank.
9. Click on save at the bottom of the form (you need to scroll)
10. Back on Odoo, click on Continue
11. A link is displayed, click on it - you may need to login again - and click
    on "Allow".
12. Back on Odoo again, click on Continue
13. Authentication is complete!


Configuration of the Backend
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Setup the webhooks
""""""""""""""""""

It is advised to setup the webhooks so the synchronizations are in realtime.

1. On the Jira Backend, set the "Base Odoo URL for Webhooks" to URL of Odoo,
   it must be reachable from Jira.
2. Click on "Install Webhooks"

Configure the Epic Link
"""""""""""""""""""""""

If you use Epics, you need to click on "Configure Epic Link", Odoo will search
the name of the custom field used for the Epic Link.

Configuration done
""""""""""""""""""

You can now click on the button "Configuration Done".

Synchronizations
^^^^^^^^^^^^^^^^

The tasks and worklogs are always imported from JIRA to Odoo, there
is no synchronization in the other direction.

Initial synchronizations
""""""""""""""""""""""""

You can already select the "Imports" tab in the Backend and click on "Link
users" and "Import issue types". The users will be matched either by login or by email.

Create and export a project
"""""""""""""""""""""""""""

Projects can be created in Odoo and exported to Jira. You can then create a
project, and use the action "Link with JIRA" and use the "Export to JIRA" action.

When you choose to export a project to JIRA, if you change the name
or the key of the project, the new values will be pushed to JIRA.

Link a project with JIRA
""""""""""""""""""""""""

If you already have a project on JIRA or prefer to create it first on JIRA,
you can link an Odoo project. Use the "Link with JIRA" action on the project
and select the "Link with JIRA" action.

This action establish the link, then changes of the name or the key on either
side are not pushed.

Issue Types on Projects
"""""""""""""""""""""""

When you link a project, you have to select which issue types are synchronized.
Only tasks of the selected types will be created in Odoo.

If a JIRA worklog is added to a type of issue that is not synchronized,
will attach to the closest task following these rules:

* if a subtask, find the parent task
* if no parent task, find the epic task (only if it is on the same project)
* if no epic, attach to the project without being linked to a task

Change synchronization configuration on a project
"""""""""""""""""""""""""""""""""""""""""""""""""

If you want to change the configuration of a project, such as which
issue types are synchronized, you can open the "Connector" tab in
the project settings and edit the "binding" with the backend.

Synchronize tasks and worklogs
""""""""""""""""""""""""""""""

If the webhooks are active, as soon as they are created in Jira they should appear in Odoo.
If they are not active, you can open the Jira Backend and run the
synchronizations manually, or activate the Scheduled Actions to run the batch
imports. It is important to select the issue types so don't miss this step (need improvement).


Known Issues
------------

* If an odoo user has no linked employee, worklogs will still be imported but
  with no employee


Design Notes
------------

Allowing several bindings per project
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The design evolved to allow more than one Jira binding per project in Odoo.
This conveniently allows to fetch tasks and worklogs for many projects in Jira,
which will be tracked in only one project in Odoo.

In order to push data to Jira, we have to apply restrictions on these
"multi-bindings" projects, as we cannot know to which binding data must
be pushed:

* Not more than one project (can be zero) can have a "Sync Action" set to
  "Export to JIRA". As this configuration pushes the name and key of the project
  to Jira, we cannot push it to more than one project.
* If we implement push of tasks to Jira, we'll have to add a way to restrict or
  choose to which project we push the task, this is not supported yet (for
  instance, add a Boolean "export tasks" on the project binding, or explicitly
  select the target binding on the task)
