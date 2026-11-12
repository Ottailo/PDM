"""Pure anchored local-calendar arithmetic; no Flask, database or runtime effects."""
import calendar
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

POLICY = {
    'month_end': 'clamp_to_last_day_then_return_to_anchor',
    'dst_gap': 'advance_by_gap',
    'dst_fold': 'earlier_instant',
    'catch_up': 'latest_due_coalesced',
}


def validate(start_local, zone, unit, count):
    if not isinstance(start_local, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}', start_local):
        raise ValueError('start_local must be YYYY-MM-DDTHH:mm without an offset')
    start = datetime.strptime(start_local, '%Y-%m-%dT%H:%M')
    if not isinstance(zone, str) or not zone or len(zone) > 64:
        raise ValueError('timezone must be a valid IANA timezone')
    try:
        tz = ZoneInfo(zone)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError('timezone must be a valid IANA timezone') from None
    if not isinstance(unit, str) or unit not in {'day', 'week', 'month'} or type(count) is not int or not 1 <= count <= 365:
        raise ValueError('Use day, week or month with interval_count 1–365')
    return start, tz


def resolve_local(local, tz):
    """Round-trip both folds: valid overlap chooses first; a gap moves forward by its size."""
    candidates = [local.replace(tzinfo=tz, fold=fold).astimezone(timezone.utc) for fold in (0, 1)]
    valid = [instant for instant in candidates if instant.astimezone(tz).replace(tzinfo=None) == local]
    if valid:
        return min(valid)
    forward = [instant for instant in candidates if instant.astimezone(tz).replace(tzinfo=None) > local]
    if not forward:
        raise ValueError('Local time cannot be resolved in this timezone')
    return min(forward)


@dataclass(frozen=True)
class Slot:
    index: int
    scheduled_local: str
    scheduled_at: datetime
    timezone: str

    def json(self):
        return {'scheduled_local': self.scheduled_local,
                'scheduled_at': self.scheduled_at.isoformat().replace('+00:00', 'Z'),
                'timezone': self.timezone}


class Calendar:
    """Fixed anchor. Search is logarithmic (at most 24 probes), never per missed period."""
    def __init__(self, start_local, zone, unit, count):
        self.start, self.tz = validate(start_local, zone, unit, count)
        self.zone, self.unit, self.count = zone, unit, count
        if unit == 'month':
            self.maximum_index = ((9999 - self.start.year) * 12 + 12 - self.start.month) // count
        else:
            days = (datetime.max.date() - self.start.date()).days
            self.maximum_index = days // (count * (7 if unit == 'week' else 1))

    def slot(self, index):
        if type(index) is not int or not 0 <= index <= self.maximum_index:
            raise ValueError('Calendar slot is outside the supported date range')
        if self.unit == 'month':
            ordinal = self.start.year * 12 + self.start.month - 1 + index * self.count
            year, month0 = divmod(ordinal, 12)
            local = self.start.replace(year=year, month=month0 + 1,
                                       day=min(self.start.day, calendar.monthrange(year, month0 + 1)[1]))
        else:
            local = self.start + timedelta(days=index * self.count * (7 if self.unit == 'week' else 1))
        return Slot(index, local.isoformat(timespec='minutes'), resolve_local(local, self.tz), self.zone)

    def latest_index(self, instant):
        if not isinstance(instant, datetime) or instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError('Clock must be an aware datetime')
        instant = instant.astimezone(timezone.utc)
        lo, hi = -1, self.maximum_index + 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            try:
                due = self.slot(mid).scheduled_at
            except (OverflowError, ValueError):
                hi = mid
                continue
            if due <= instant:
                lo = mid
            else:
                hi = mid
        return lo

    def future_index(self, instant):
        index = self.latest_index(instant) + 1
        if index > self.maximum_index:
            raise ValueError('No future calendar slot in the supported date range')
        return index

    def preview(self, instant, limit=5):
        if type(limit) is not int or not 1 <= limit <= 5:
            raise ValueError('Preview limit must be 1–5')
        first = max(0, self.latest_index(instant) + 1)
        return [self.slot(index).json() for index in range(first, min(first + limit, self.maximum_index + 1))]
