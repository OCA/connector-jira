import time
from datetime import date, datetime

from odoo import fields

MILLI_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
MILLI_DATETIME_LENGTH = len(MILLI_DATETIME_FORMAT)


class MilliDatetime(fields.Field):
    """Field storing Datetime with milliseconds precision

    There are no widgets for this field, it is only technical
    for storing Jira timestamps.

    As Jira uses Unix Timestamps on some webservices methods,
    this field provides conversions utilities.

    Beware, unlike the Datetime field (prior 12.0), the MilliDatetime
    field works with datetime objects.
    """

    type = "millidatetime"
    column_type = ("timestamp", "timestamp")

    @staticmethod
    def from_string(value):
        """Convert a string to :class:`datetime` including milliseconds"""
        if not value:
            return None
        if isinstance(value, datetime):
            if value.tzinfo:
                raise ValueError(
                    "MilliDatetime field expects a naive datetime: %s" % value
                )
            return value
        if len(value) > fields.DATETIME_LENGTH:
            return datetime.strptime(value, MILLI_DATETIME_FORMAT)
        else:
            return fields.Datetime.from_string(value)

    @staticmethod
    def to_string(value):
        """Convert a :class:`datetime` including milliseconds to a string"""
        return value.strftime(MILLI_DATETIME_FORMAT) if value else False

    @staticmethod
    def from_timestamp(value):
        return datetime.fromtimestamp(value / 1000)

    @staticmethod
    def to_timestamp(value):
        assert not value.tzinfo
        return int(time.mktime(value.timetuple()) * 1000 + value.microsecond / 1000)

    def convert_to_cache(self, value, record, validate=True):
        if not value:
            return False
        if isinstance(value, date) and not isinstance(value, datetime):
            raise TypeError(
                "%s (field %s) must be string or datetime" ", not date." % (value, self)
            )
        return self.from_string(value)
