# -*- coding: utf-8 -*-
# Copyright 2016 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import pytz
from dateutil import parser

from openerp.addons.connector.unit import mapper


def iso8601_to_utc_datetime(isodate):
    """ Returns the UTC datetime from an iso8601 date

    A QoQa date is formatted using the ISO 8601 format.
    Example: 2013-11-04T13:52:01+0100
    """
    parsed = parser.parse(isodate)
    if not parsed.tzinfo:
        return parsed
    utc = pytz.timezone('UTC')
    # set as UTC and then remove the tzinfo so the date becomes naive
    return parsed.astimezone(utc).replace(tzinfo=None)


def utc_datetime_to_iso8601(dt):
    """ Returns an iso8601 datetime from a datetime.

    Example: 2013-11-04 12:52:01 → 2013-11-04T12:52:01+0000

    """
    utc = pytz.timezone('UTC')
    utc_dt = utc.localize(dt, is_dst=False)  # UTC = no DST
    return utc_dt.isoformat()


class FromFields(mapper.Mapper):

    @mapper.mapping
    def values_from_attributes(self, record):
        values = {}
        from_fields_mappings = getattr(self, 'from_fields', [])
        fields_values = record.get('fields', {})
        for source, target in from_fields_mappings:
            values[target] = self._map_direct(fields_values, source, target)
        return values
