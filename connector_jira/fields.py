import time

from datetime import datetime

from odoo import fields
from odoo.tools import pycompat

MILLI_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"


class MillisecondsUnixTimestamp(fields.Field):
    """Field storing and reading timestamps as Unix format

    It keeps a precision including milliseconds.
    """
    type = 'millisecondsunixtimestamp'
    column_type = ('timestamp', 'timestamp')

    @staticmethod
    def from_string(value):
        """Convert a string to :class:`datetime` including milliseconds"""
        if not value:
            return None
        if len(value) == len(MILLI_DATETIME_FORMAT):
            return datetime.strptime(value, MILLI_DATETIME_FORMAT)
        else:
            return fields.Datetime.from_string(value)

    @staticmethod
    def to_string(value):
        """Convert a :class:`datetime` including milliseconds to a string"""
        return value.strftime(MILLI_DATETIME_FORMAT) if value else False

    @staticmethod
    def unix_to_datetime(value):
        return datetime.fromtimestamp(value / 1000)

    @staticmethod
    def datetime_to_unix(value):
        return int(
            time.mktime(value.timetuple()) * 1000 +
            value.microsecond / 1000
        )

    def convert_to_column(self, value, record, values=None):
        """ Convert ``value`` from the ``write`` format to the SQL format. """
        if value is None or value is False:
            return None
        return datetime.fromtimestamp(value / 1000)

    def convert_to_cache(self, value, record, validate=True):
        if not value:
            return False

        if isinstance(value, pycompat.string_types):
            value = self.from_string(value)
        if isinstance(value, datetime):
            value = self.datetime_to_unix(value)
        return value
