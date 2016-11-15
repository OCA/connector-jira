# -*- coding: utf-8 -*-
# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from .unit.exporter import export_record


def delay_export(session, model_name, record_id, vals, **kwargs):
    """ Delay a job which export a binding record.

    (A binding record being a ``jira.res.partner``,
    ``jira.product.product``, ...)

    The additional kwargs are passed to ``delay()``, they can be:
        ``priority``, ``eta``, ``max_retries``.
    """
    if session.env.context.get('connector_no_export'):
        return
    fields = vals.keys()
    export_record.delay(session, model_name, record_id,
                        fields=fields, **kwargs)


def delay_export_all_bindings(session, model_name, record_id, vals,
                              **kwargs):
    """ Delay a job which export all the bindings of a record.

    In this case, it is called on records of normal models and will delay
    the export for all the bindings.

    The additional kwargs are passed to ``delay()``, they can be:
        ``priority``, ``eta``, ``max_retries``.
    """
    if session.env.context.get('connector_no_export'):
        return
    model = session.env[model_name]
    record = model.browse(record_id)
    fields = vals.keys()
    for binding in record.jira_bind_ids:
        export_record.delay(session, binding._model._name, binding.id,
                            fields=fields, **kwargs)
