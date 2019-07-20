You need the following Python packages:

* requests
* jira
* oauthlib
* requests-oauthlib
* requests-toolbelt
* PyJWT
* cryptography

Once the addon is installed, follow these steps:

Job Queue
~~~~~~~~~

In ``odoo.conf``, configure similarly:

.. code-block::

  [queue_job]
  channels = root:1,root.connector_jira.import:2


Backend
~~~~~~~

1. Open the menu Connectors > Jira > Backends
2. Create a new Jira Backend

   * Put the name you want
   * Set the URL of your Jira, like https://jira.example.com
   * You can also select the company where records will be created and the
     default project template used when Odoo will create the projects in Jira

3. Save and continue with the Authentication

Authentication of Backend
~~~~~~~~~~~~~~~~~~~~~~~~~

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
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Setup the webhooks**

It is advised to setup the webhooks so the synchronizations are in realtime.

1. On the Jira Backend, set the "Base Odoo URL for Webhooks" to URL of Odoo,
   it must be reachable from Jira.
2. Click on "Install Webhooks"

**Configure the Epic Link**

If you use Epics, you need to click on "Configure Epic Link", Odoo will search
the name of the custom field used for the Epic Link.

**Configuration done**

You can now click on the button "Configuration Done".
