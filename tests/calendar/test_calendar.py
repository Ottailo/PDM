"""Standalone pure-calendar tests: run with --noconftest, no application imports."""
import importlib.util
from pathlib import Path
import sys
from datetime import datetime, timezone
import pytest

PATH = Path(__file__).resolve().parents[2]/'app'/'pilot'/'calendar.py'
spec = importlib.util.spec_from_file_location('pdm_calendar_under_test',PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
Calendar = module.Calendar


def utc(value):
    return datetime.fromisoformat(value.replace('Z','+00:00'))


def test_month_end_returns_to_anchor_and_leap_year():
    cal = Calendar('2024-01-31T09:00','Africa/Lagos','month',1)
    assert [cal.slot(i).scheduled_local for i in range(4)] == ['2024-01-31T09:00','2024-02-29T09:00','2024-03-31T09:00','2024-04-30T09:00']
    nonleap = Calendar('2025-01-31T09:00','Africa/Lagos','month',1)
    assert nonleap.slot(1).scheduled_local=='2025-02-28T09:00'
    assert nonleap.slot(2).scheduled_local=='2025-03-31T09:00'


def test_leap_anchor_and_multiple_month_interval():
    cal = Calendar('2024-02-29T12:00','UTC','month',12)
    assert cal.slot(1).scheduled_local=='2025-02-28T12:00'
    assert cal.slot(4).scheduled_local=='2028-02-29T12:00'
    assert Calendar('2024-12-31T12:00','UTC','month',2).slot(1).scheduled_local=='2025-02-28T12:00'


def test_dst_gap_advances_by_gap_not_to_start_of_hour():
    cal = Calendar('2026-03-08T02:30','America/New_York','day',1)
    assert cal.slot(0).scheduled_at==utc('2026-03-08T07:30Z')
    assert cal.slot(0).scheduled_local=='2026-03-08T02:30'
    assert cal.slot(1).scheduled_at==utc('2026-03-09T06:30Z')
    half = Calendar('2026-10-04T02:15','Australia/Lord_Howe','day',1)
    assert half.slot(0).scheduled_at==utc('2026-10-03T15:45Z')


def test_dst_fold_chooses_earlier_instant():
    cal = Calendar('2026-11-01T01:30','America/New_York','day',1)
    assert cal.slot(0).scheduled_at==utc('2026-11-01T05:30Z')
    assert cal.slot(1).scheduled_at==utc('2026-11-02T06:30Z')


def test_local_day_and_week_do_not_use_fixed_utc_duration():
    cal = Calendar('2026-03-07T09:00','America/New_York','day',1)
    assert (cal.slot(1).scheduled_at-cal.slot(0).scheduled_at).total_seconds()==23*3600
    weekly = Calendar('2026-03-01T09:00','America/New_York','week',1)
    assert (weekly.slot(1).scheduled_at-weekly.slot(0).scheduled_at).total_seconds()==167*3600


def test_bounded_catchup_over_millions_of_days(monkeypatch):
    cal = Calendar('0001-01-01T00:00','UTC','day',1)
    original = cal.slot
    calls = []
    def counted(index):
        calls.append(index)
        return original(index)
    monkeypatch.setattr(cal,'slot',counted)
    instant = utc('9998-12-31T23:59Z')
    assert cal.latest_index(instant)==(instant.date()-datetime(1,1,1).date()).days
    assert len(calls)<=24


def test_exact_boundary_future_preview_and_no_completion_drift():
    cal = Calendar('2026-01-31T09:00','Africa/Lagos','month',1)
    assert cal.latest_index(utc('2026-01-31T07:59Z'))==-1
    assert cal.latest_index(utc('2026-01-31T08:00Z'))==0
    assert cal.future_index(utc('2026-02-28T08:00Z'))==2
    dates = cal.preview(utc('2026-02-28T08:00Z'))
    assert len(dates)==5 and dates[0]['scheduled_local']=='2026-03-31T09:00'
    assert dates[0]['timezone']=='Africa/Lagos'
    assert dates[0]['scheduled_at']=='2026-03-31T08:00:00Z'


@pytest.mark.parametrize('start,zone,unit,count',[
    ('2026-01-01T09:00Z','UTC','day',1),('2026-01-01T09:00+01:00','UTC','day',1),
    ('2026-02-30T09:00','UTC','day',1),('2026-1-01T09:00','UTC','day',1),
    ('2026-01-01T09:00','Not/A_Zone','day',1),('2026-01-01T09:00','UTC','cron',1),
    ('2026-01-01T09:00','UTC','day',True),('2026-01-01T09:00','UTC','day',0),
    ('2026-01-01T09:00','UTC','day',366)])
def test_invalid_controls_rejected(start,zone,unit,count):
    with pytest.raises(ValueError):
        Calendar(start,zone,unit,count)


def test_naive_clock_and_unbounded_preview_rejected():
    cal = Calendar('2026-01-01T09:00','UTC','day',1)
    with pytest.raises(ValueError):
        cal.latest_index(datetime(2026,1,1))
    with pytest.raises(ValueError):
        cal.preview(datetime.now(timezone.utc),6)
    with pytest.raises(ValueError):
        cal.slot(-1)
