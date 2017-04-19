# -*- coding: utf-8 -*-
# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


def delay_export(env, model_name, record_id, vals, **job_kwargs):
    """ Delay a job which export a binding record.

    (A binding record being a ``jira.res.partner``,
    ``jira.product.product``, ...)

    The additional kwargs are passed to ``with_delay()``, they can be:
        ``priority``, ``eta``, ``max_retries``.
    """
    if env.context.get('connector_no_export'):
        return
    binding = env[model_name].browse(record_id)
    fields = vals.keys()
    binding.with_delay(**job_kwargs).export_record(fields=fields)


def delay_export_all_bindings(env, model_name, record_id, vals,
                              **job_kwargs):
    """ Delay a job which export all the bindings of a record.

    In this case, it is called on records of normal models and will delay
    the export for all the bindings.

    The additional kwargs are passed to ``with_delay()``, they can be:
        ``priority``, ``eta``, ``max_retries``.
    """
    if env.context.get('connector_no_export'):
        return
    if (vals.keys() == ['esb_bind_ids'] or
            vals.keys() == ['message_follower_ids']):
        # When vals is esb_bind_ids:
        # Binding edited from the record's view.  When only this
        # field has been modified, an other job has already been delayed for
        # the binding record so can exit this event early.

        # When vals is message_follower_ids:
        # MailThread.message_subscribe() has been called, this
        # method does a write on the field message_follower_ids,
        # we never want to export that.
        return
    record = env[model_name].browse(record_id)
    for binding in record.jira_bind_ids:
        delay_export(env, binding._name, binding.id, vals, **job_kwargs)
