from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from app.parking import (
    DEFAULT_SNAPSHOT,
    SNAPSHOT_AS_OF,
    DemoDataAdapter,
    QueueEvent,
    QueueTicket,
)


def adapter(snapshot=DEFAULT_SNAPSHOT, delta=timedelta()):
    return DemoDataAdapter(SNAPSHOT_AS_OF + delta, snapshot)


def queue_metric(result, queue_id="loading"):
    return next(row for row in result["queues"] if row["queue_id"] == queue_id)


def test_default_fixture_counts_and_forecast_are_deterministic():
    first = adapter()
    second = adapter()
    assert first.parking_status()["active_parking_vehicle_count"] == 14
    assert [row["waiting_vehicle_count"] for row in first.parking_status()["queues"]] == [12, 3, 0]
    assert first.metrics() == second.metrics()
    assert queue_metric(first.metrics())["estimated_clear_minutes"] == 120
    assert first.metrics()["parking_duration"]["average_minutes"] == 27.5


def test_clock_shift_does_not_move_fixture_or_change_metrics():
    before = adapter()
    shifted = adapter(delta=timedelta(minutes=1))
    assert shifted.snapshot.data_as_of == before.snapshot.data_as_of
    assert shifted.metrics()["queues"] == before.metrics()["queues"]


def test_staleness_boundary_is_exactly_300_seconds():
    assert adapter(delta=timedelta(seconds=300)).freshness == "fresh"
    assert adapter(delta=timedelta(seconds=301)).freshness == "stale"
    metric = queue_metric(adapter(delta=timedelta(seconds=301)).metrics())
    assert metric["estimated_clear_minutes"] is None
    assert metric["forecast_reason"] == "STALE_DATA"


def test_future_snapshot_suppresses_forecast():
    metric = queue_metric(adapter(delta=timedelta(seconds=-1)).metrics())
    assert metric["forecast_reason"] == "FUTURE_DATA"
    assert metric["estimated_clear_minutes"] is None


def test_observation_window_is_open_at_start_closed_at_end():
    snapshot = DEFAULT_SNAPSHOT
    events = snapshot.queue_events + (
        QueueEvent("edge-open", "queue_join", "loading", "loading", "edge-open", SNAPSHOT_AS_OF - timedelta(hours=1)),
        QueueEvent("edge-closed", "service_start", "loading", "loading", "edge-open", SNAPSHOT_AS_OF),
    )
    metric = queue_metric(adapter(replace(snapshot, queue_events=events)).metrics())
    assert metric["valid_arrivals"] == 4
    assert metric["valid_service_starts"] == 11


def test_event_ids_are_unique_across_queue_partitions():
    repeated = DEFAULT_SNAPSHOT.queue_events[0]
    foreign = QueueEvent(
        repeated.event_id, "queue_join", "unloading", "unloading", "other", SNAPSHOT_AS_OF - timedelta(minutes=5)
    )
    metrics = adapter(replace(DEFAULT_SNAPSHOT, queue_events=DEFAULT_SNAPSHOT.queue_events + (foreign,))).metrics()
    assert queue_metric(metrics, "loading")["forecast_reason"] == "INCONSISTENT_DATA"
    assert queue_metric(metrics, "unloading")["forecast_reason"] == "INCONSISTENT_DATA"


def test_incomplete_observation_coverage_disables_forecast():
    snapshot = replace(DEFAULT_SNAPSHOT, coverage_start=SNAPSHOT_AS_OF - timedelta(minutes=59))
    metric = queue_metric(adapter(snapshot).metrics())
    assert metric["forecast_reason"] == "INSUFFICIENT_HISTORY"
    assert metric["estimated_clear_minutes"] is None


def test_fewer_than_ten_service_starts_disables_forecast():
    events = tuple(event for event in DEFAULT_SNAPSHOT.queue_events if event.event_id != "start-served-0")
    metric = queue_metric(adapter(replace(DEFAULT_SNAPSHOT, queue_events=events)).metrics())
    assert metric["valid_service_starts"] == 9
    assert metric["forecast_reason"] == "INSUFFICIENT_OBSERVATIONS"


@pytest.mark.parametrize("extra_arrivals", [6, 7])
def test_zero_or_negative_net_service_rate_disables_forecast(extra_arrivals):
    additions = tuple(
        QueueEvent(f"extra-{i}", "queue_join", "loading", "loading", f"extra-{i}", SNAPSHOT_AS_OF - timedelta(minutes=5))
        for i in range(extra_arrivals)
    )
    metric = queue_metric(adapter(replace(DEFAULT_SNAPSHOT, queue_events=DEFAULT_SNAPSHOT.queue_events + additions)).metrics())
    assert metric["forecast_reason"] == "NON_POSITIVE_NET_RATE"
    assert metric["estimated_clear_minutes"] is None


def test_other_process_cannot_be_mixed_into_loading_rate():
    event = QueueEvent("wrong-process", "queue_join", "loading", "unloading", "private-marker", SNAPSHOT_AS_OF - timedelta(minutes=4))
    metric = queue_metric(adapter(replace(DEFAULT_SNAPSHOT, queue_events=DEFAULT_SNAPSHOT.queue_events + (event,))).metrics())
    assert metric["forecast_reason"] == "PROCESS_MISMATCH"
    assert metric["estimated_clear_minutes"] is None


def test_duplicate_and_future_events_are_excluded_and_mark_inconsistent():
    original = DEFAULT_SNAPSHOT.queue_events[0]
    future = QueueEvent("after-asof", "queue_join", "loading", "loading", "fake", SNAPSHOT_AS_OF + timedelta(seconds=1))
    snapshot = replace(DEFAULT_SNAPSHOT, queue_events=DEFAULT_SNAPSHOT.queue_events + (original, future))
    metric = queue_metric(adapter(snapshot).metrics())
    assert metric["excluded_events"] == 4
    assert metric["forecast_reason"] == "INCONSISTENT_DATA"
    assert metric["estimated_clear_minutes"] is None


def test_service_start_before_queue_join_is_inconsistent():
    events = tuple(
        replace(event, occurred_at=SNAPSHOT_AS_OF - timedelta(minutes=130))
        if event.event_id == "start-served-0" else event
        for event in DEFAULT_SNAPSHOT.queue_events
    )
    metric = queue_metric(adapter(replace(DEFAULT_SNAPSHOT, queue_events=events)).metrics())
    assert metric["valid_service_starts"] == 9
    assert metric["forecast_reason"] == "INCONSISTENT_DATA"


def test_empty_queue_has_explicit_reason_and_zero_waiting():
    tickets = tuple(ticket for ticket in DEFAULT_SNAPSHOT.queue_tickets if ticket.queue_id != "loading" or ticket.service_started_at)
    metric = queue_metric(adapter(replace(DEFAULT_SNAPSHOT, queue_tickets=tickets)).metrics())
    assert metric["waiting_vehicle_count"] == 0
    assert metric["forecast_reason"] == "EMPTY_QUEUE"
    assert metric["estimated_clear_minutes"] is None


def test_duplicate_active_vehicle_is_counted_once():
    duplicate = QueueTicket("duplicate", "loading", "loading", "waiting-0", SNAPSHOT_AS_OF - timedelta(minutes=8))
    altered = adapter(replace(DEFAULT_SNAPSHOT, queue_tickets=DEFAULT_SNAPSHOT.queue_tickets + (duplicate,)))
    status = altered.parking_status()
    metric = queue_metric(altered.metrics())
    assert status["active_parking_vehicle_count"] == 14
    assert status["queues"][0]["waiting_vehicle_count"] == 12
    assert metric["forecast_reason"] == "INCONSISTENT_DATA"
    assert metric["estimated_clear_minutes"] is None


def test_duplicate_parking_session_id_is_excluded():
    duplicate = DEFAULT_SNAPSHOT.parking_sessions[0]
    altered = adapter(replace(DEFAULT_SNAPSHOT, parking_sessions=DEFAULT_SNAPSHOT.parking_sessions + (duplicate,)))
    assert altered.parking_status()["active_parking_vehicle_count"] == 14
    assert altered.parking_status()["excluded_invalid_records"] == 1


def test_empty_and_invalid_completed_parking_samples_return_null():
    active = tuple(session for session in DEFAULT_SNAPSHOT.parking_sessions if session.exited_at is None)
    empty = adapter(replace(DEFAULT_SNAPSHOT, parking_sessions=active)).metrics()["parking_duration"]
    invalid = (
        DEFAULT_SNAPSHOT.parking_sessions[0],
        replace(DEFAULT_SNAPSHOT.parking_sessions[-1], entered_at=datetime(2026, 10, 10, 6), exited_at=SNAPSHOT_AS_OF),
        replace(DEFAULT_SNAPSHOT.parking_sessions[-1], session_id="future-exit", exited_at=SNAPSHOT_AS_OF + timedelta(seconds=1)),
    )
    rejected = adapter(replace(DEFAULT_SNAPSHOT, parking_sessions=invalid)).metrics()["parking_duration"]
    assert empty["average_minutes"] is None and empty["completed_sessions"] == 0
    assert rejected["average_minutes"] is None and rejected["excluded_sessions"] == 2


def test_naive_demo_clock_is_rejected():
    from datetime import datetime

    with pytest.raises(ValueError, match="timezone-aware"):
        DemoDataAdapter(datetime(2026, 10, 10, 7))


def test_offset_aware_snapshot_is_returned_in_utc():
    offset = timezone(timedelta(hours=5))
    local_as_of = SNAPSHOT_AS_OF.astimezone(offset)
    snapshot = replace(
        DEFAULT_SNAPSHOT,
        data_as_of=local_as_of,
        coverage_start=DEFAULT_SNAPSHOT.coverage_start.astimezone(offset),
        coverage_end=DEFAULT_SNAPSHOT.coverage_end.astimezone(offset),
    )
    result = adapter(snapshot).metrics()
    assert result["data_as_of"].isoformat().endswith("+00:00")
    assert result["queues"][0]["coverage_start"].isoformat().endswith("+00:00")
