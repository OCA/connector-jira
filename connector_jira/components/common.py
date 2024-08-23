# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from datetime import datetime

import pytz
from dateutil import parser

from odoo import fields

JIRA_JQL_DATETIME_FORMAT = "%Y-%m-%d %H:%M"  # no seconds :-(
RETRY_ON_ADVISORY_LOCK = 1  # seconds
RETRY_WHEN_CONCURRENT_DETECTED = 1  # seconds
# when we import using JQL, we always import tasks from
# slightly before the last batch import, because Jira
# does not send the results from the past minute and
# maybe sometimes more
IMPORT_DELTA = 300  # seconds


def iso8601_to_utc_datetime(isodate):
    """Returns the UTC datetime from an iso8601 date

    A JIRA date is formatted using the ISO 8601 format.
    Example: 2013-11-04T13:52:01+0100
    """
    parsed = parser.parse(isodate)
    if not parsed.tzinfo:
        return parsed
    # set as UTC and then remove the tzinfo so the date becomes naive
    return parsed.astimezone(pytz.UTC).replace(tzinfo=None)


def utc_datetime_to_iso8601(dt):
    """Returns an iso8601 datetime from a datetime.

    Example: 2013-11-04 12:52:01 → 2013-11-04T12:52:01+0000

    """
    utc_dt = pytz.UTC.localize(dt, is_dst=False)  # UTC = no DST
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
    return datetime.strptime(isodate[:10], "%Y-%m-%d").date()


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
