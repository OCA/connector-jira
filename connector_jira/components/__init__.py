# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

# ⚠️⚠️⚠️
# 1) in order to ease readability and maintainability, components have been split into
#    multiple files, each containing exactly 1 component
# 2) components' import is sorted so that no dependency issue should arise
# 3) next to each import, a comment will describe the components' dependencies
# 4) when adding new components, please make sure it inherits (directly or indirectly)
#    from ``jira.base``
# ⚠️⚠️⚠️

# Base abstract component
from . import jira_base  # base.connector

# Inheriting abstract components
from . import jira_base_exporter  # base.exporter, jira.base
from . import jira_batch_importer  # base.importer, jira.base
from . import jira_delayed_batch_importer  # jira.batch.importer
from . import jira_direct_batch_importer  # jira.batch.importer
from . import jira_import_mapper  # base.import.mapper, jira.base
from . import jira_timestamp_batch_importer  # base.importer, jira.base

# Generic components
from . import jira_binder  # base.binder, jira.base
from . import jira_deleter  # base.deleter, jira.base
from . import jira_exporter  # jira.base.exporter
from . import jira_importer  # base.importer, jira.base
from . import jira_webservice_adapter  # base.backend.adapter.crud, jira.base

# Specific components
from . import jira_analytic_line_batch_importer  # jira.timestamp.batch.importer
from . import jira_analytic_line_importer  # jira.importer
from . import jira_analytic_line_mapper  # jira.import.mapper
from . import jira_analytic_line_timestamp_batch_deleter  # base.synchronizer, jira.base
from . import jira_backend_adapter  # jira.webservice.adapter
from . import jira_issue_type_adapter  # jira.webservice.adapter
from . import jira_issue_type_batch_importer  # jira.direct.batch.importer
from . import jira_issue_type_mapper  # jira.import.mapper
from . import jira_mapper_from_attrs  # jira.base
from . import jira_model_binder  # base.binder, jira.base
from . import jira_project_adapter  # jira.webservice.adapter
from . import jira_project_binder  # jira.binder
from . import jira_project_project_listener  # base.connector.listener, jira.base
from . import jira_project_project_exporter  # jira.exporter
from . import jira_project_task_adapter  # jira.webservice.adapter
from . import jira_project_task_batch_importer  # jira.timestamp.batch.importer
from . import jira_project_task_importer  # jira.importer
from . import jira_project_task_mapper  # jira.import.mapper
from . import jira_res_users_adapter  # jira.webservice.adapter
from . import jira_res_users_importer  # jira.importer
from . import jira_task_project_matcher  # jira.base
from . import jira_worklog_adapter  # jira.webservice.adapter
from . import project_project_listener  # base.connector.listener, jira.base
