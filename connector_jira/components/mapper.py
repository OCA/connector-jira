# Copyright 2016-2019 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from datetime import datetime

import pytz
from dateutil import parser

from odoo import fields

from odoo.addons.component.core import AbstractComponent, Component
from odoo.addons.connector.components.mapper import mapping


class JiraImportMapper(AbstractComponent):
    """Base Import Mapper for Jira"""

    _name = "jira.import.mapper"
    _inherit = ["base.import.mapper", "jira.base"]

    @mapping
    def jira_updated_at(self, record):
        if self.options.external_updated_at:
            return {"jira_updated_at": self.options.external_updated_at}


def iso8601_to_utc_datetime(isodate):
    """Returns the UTC datetime from an iso8601 date

    A JIRA date is formatted using the ISO 8601 format.
    Example: 2013-11-04T13:52:01+0100
    """
    parsed = parser.parse(isodate)
    if not parsed.tzinfo:
        return parsed
    utc = pytz.timezone("UTC")
    # set as UTC and then remove the tzinfo so the date becomes naive
    return parsed.astimezone(utc).replace(tzinfo=None)


def utc_datetime_to_iso8601(dt):
    """Returns an iso8601 datetime from a datetime.

    Example: 2013-11-04 12:52:01 → 2013-11-04T12:52:01+0000

    """
    utc = pytz.timezone("UTC")
    utc_dt = utc.localize(dt, is_dst=False)  # UTC = no DST
    return utc_dt.isoformat()


def iso8601_to_utc(field):
    """A modifier intended to be used on the ``direct`` mappings for
    importers.

    A Jira date is formatted using the ISO 8601 format.
    Convert an ISO 8601 timestamp to an UTC datetime as string
    as expected by Odoo.

    Example: 2013-11-04T13:52:01+0100 -> 2013-11-04 12:52:01

    Usage::

        direct = [(iso8601_to_utc('date_field'), 'date_field')]

    :param field: name of the source field in the record

    """

    def modifier(self, record, to_attr):
        value = record.get(field)
        if not value:
            return False
        utc_date = iso8601_to_utc_datetime(value)
        return fields.Datetime.to_string(utc_date)

    return modifier


def iso8601_to_naive_date(isodate):
    """Returns the naive date from an iso8601 date

    Keep only the date, when we want to keep only the naive date.
    It's safe to extract it directly from the tz-aware timestamp.
    Example with 2014-10-07T00:34:59+0200: we want 2014-10-07 and not
    2014-10-06 that we would have using the timestamp converted to UTC.
    """
    naive_date = isodate[:10]
    return datetime.strptime(naive_date, "%Y-%m-%d").date()


def iso8601_naive_date(field):
    """A modifier intended to be used on the ``direct`` mappings for
    importers.

    A JIRA datetime is formatted using the ISO 8601 format.
    Returns the naive date from an iso8601 datetime.

    Keep only the date, when we want to keep only the naive date.
    It's safe to extract it directly from the tz-aware timestamp.
    Example with 2014-10-07T00:34:59+0200: we want 2014-10-07 and not
    2014-10-06 that we would have using the timestamp converted to UTC.

    Usage::

        direct = [(iso8601_naive_date('name'), 'name')]

    :param field: name of the source field in the record

    """

    def modifier(self, record, to_attr):
        value = record.get(field)
        if not value:
            return False
        naive_date = iso8601_to_naive_date(value)
        return fields.Date.to_string(naive_date)

    return modifier


def follow_dict_path(field):
    """A modifier intended to be used on ``direct`` mappings.

    'Follows' children keys in dictionaries
    If a key is missing along the path, ``None`` is returned.

    Examples:
        Assuming a dict `{'a': {'b': 1}}

        direct = [
            (follow_dict_path('a.b'), 'cat')]

        Then 'cat' will be 1.

    :param field: field "path", using dots for subkeys
    """

    def modifier(self, record, to_attr):
        attrs = field.split(".")
        value = record
        for attr in attrs:
            value = value.get(attr)
            if not value:
                break
        return value

    return modifier


def whenempty(field, default_value):
    """Set a default value when the value is evaluated to False

    A modifier intended to be used on the ``direct`` mappings.

    Example::

        direct = [(whenempty('source', 'default value'), 'target')]

    :param field: name of the source field in the record
    :param default_value: value to set when the source value is False-ish
    """

    def modifier(self, record, to_attr):
        value = record[field]
        if not value:
            return default_value
        return value

    return modifier


class FromFields(Component):
    _name = "jira.mapper.from.attrs"
    _inherit = ["jira.base"]
    _usage = "map.from.attrs"

    def values(self, record, mapper_):
        values = {}
        from_fields_mappings = getattr(mapper_, "from_fields", [])
        fields_values = record.get("fields", {})
        for source, target in from_fields_mappings:
            values[target] = mapper_._map_direct(fields_values, source, target)
        return values
