* If an odoo user has no linked employee, worklogs will still be imported but
  with no employee.

**Allowing several bindings per project**

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
