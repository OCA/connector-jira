You need the following Python packages:

- requests
- jira
- oauthlib
- requests-oauthlib
- requests-toolbelt
- PyJWT
- cryptography
- atlassian-jwt

Once the addon is installed, follow these steps:

## Job Queue

In `odoo.conf`, configure similarly:

``` 
[queue_job]
channels = root:1,root.connector_jira.import:2
```

## Backend

1.  Open the menu Connectors \> Jira \> Backends
2.  Create a new Jira Backend
    - Put the name you want
    - You can also select the company where records will be created and
      the default project template used when Odoo will create the
      projects in Jira
    - Save
3.  Make note of the value of the App Descriptor URL (important: make
    sure that the system parameter web.base.url is set properly. For
    local development you will want to use ngrok to make your computer
    reachable over https from Jira Cloud).

## Installing the backend as a Jira App

In case this gets outdated, refer to
<https://developer.atlassian.com/platform/marketplace/listing-connect-apps/#list-a-connect-app>

1.  Login on marketplace.atlassian.com (possibly create an account)
2.  On the top right corner, the icon with your avatar leads to a menu
    -\> select the Publish an App entry
3.  On the Publish a new app screen:
    - select a Vendor (normally your company)
    - upload your app: select Provide a URL to your artifact
    - click on the Enter URL button
    - paste the App Descriptor URL in the pop-up and click on the Done
      button
    - the Name field should get populated from the name of your backend
    - Compatible application: select Jira
    - build number: can be kept as is
4.  Click on the Save as private button (!) Important: do not click the
    "Next: Make public" button. That flow would allow anyone on Jira
    Cloud to install your backend.
5.  On the next screen, you can go to the "Private Listings" page, and
    click on the "Create a token" button: this token can be used to
    install the app on your Jira instance.

## Installing the Jira App on your Jira Cloud instance

1.  Connect to your Jira instance with an account with Admin access
2.  In the Apps menu, select Manage your apps
3.  In the Apps screen, click on the Settings link which is under the
    User-installed apps list
4.  In the settings screen, check the Enable private listings box, and
    click on Apply
5.  Refresh the Apps page: you should see an Upload app link: click on
    it
6.  On the Upload app dialog, paste the token URL you received in the
    previous procedure, and click on Upload

## Configuration of the Backend

Going back to Odoo, the backend should now be in the Running state, with
some information filled in, such as the Jira URI.

**Configure the Epic Link**

If you use Epics, you need to click on "Configure Epic Link", Odoo will
search the name of the custom field used for the Epic Link.

Congratulations, you're done!
