# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

# Must imported be before the others to instantiate the abstract model inherited by
# other models
from . import jira_binding

from . import account_analytic_line
from . import jira_account_analytic_line
from . import jira_backend
from . import jira_backend_timestamp
from . import jira_issue_type
from . import jira_project_base_mixin
from . import jira_project_project
from . import jira_project_task
from . import jira_res_users
from . import project_project
from . import project_task
from . import queue_job
from . import res_users
