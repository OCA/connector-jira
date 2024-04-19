On Jira Cloud, runs on a separate server, and uses OAuth2 for authorization. 

You will need to:

* configure a webservice backend for Tempo on the jira backend (choose the preconfigured one based on your region)
* configure an App for Oauth2 on Tempo by going on https://YOURINSTANCE.atlassian.net/plugins/servlet/ac/io.tempo.jira/tempo-app#!/configuration/identity-service and following the steps to create a new Application
  * Provide a name such as "Odoo of MyCompany"
  * The redirect URI is https://WEB.BASE.URL/webservice/BACKEND_ID/Oauth2/redirect
  * Client type is "confidential"
* create the app, and save the client id and client secret
* you will need so save them in an environment variable or an server environment file for the server environment configuration, something like

        [webservice_backend.tempo-eu]
        oauth2_authorization_url = https://c2c-test.atlassian.net/plugins/servlet/ac/io.tempo.jira/oauth-authorize
        oauth2_clientid = CLIENT ID
        oauth2_client_secret = CLIENT SECRET

* restart Odoo to get the parameters loaded in the record
* in Odoo web client browse to the webservice backend, and click on the "Oauth Authorize" button to complete the signup dance. Be sure to use an accound that has enough rights on Tempo to read all the timesheets from all teams. 
* you should now be ready to synchronize your Tempo worklogs in Odoo