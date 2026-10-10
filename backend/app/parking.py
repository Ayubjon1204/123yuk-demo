from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal, TypedDict

DEMO_NOTICE = "Bu alohida backend demo ma’lumoti; haqiqiy dashboard bilan sinxron emas."
SNAPSHOT_AS_OF = datetime(2026, 10, 10, 7, tzinfo=UTC)
DEMO_FACTORY = "demo-factory"
QUEUE_TYPES = {"loading": "loading", "unloading": "unloading", "other": "other"}
ForecastReason = Literal[
    "EMPTY_QUEUE", "FUTURE_DATA", "STALE_DATA", "INSUFFICIENT_HISTORY",
    "INSUFFICIENT_OBSERVATIONS", "NON_POSITIVE_NET_RATE", "PROCESS_MISMATCH", "INCONSISTENT_DATA",
]


class DemoMetadata(TypedDict):
    mode: Literal["demo"]
    source: Literal["demo_snapshot"]
    demo_notice: str
    demo_now: datetime
    data_as_of: datetime
    freshness: Literal["fresh", "stale", "future"]


class QueueStatus(TypedDict):
    queue_id: str
    service_type: str
    waiting_vehicle_count: int


class ParkingStatus(DemoMetadata):
    active_parking_vehicle_count: int
    queues: list[QueueStatus]
    excluded_invalid_records: int


class ParkingDurationMetric(TypedDict):
    window_start: datetime
    window_end: datetime
    completed_sessions: int
    excluded_sessions: int
    average_minutes: float | None


class QueueMetric(TypedDict):
    queue_id: str
    service_type: str
    window_start: datetime
    window_end: datetime
    coverage_start: datetime | None
    coverage_end: datetime | None
    waiting_vehicle_count: int
    valid_arrivals: int
    valid_service_starts: int
    excluded_events: int
    arrival_rate_per_hour: float
    service_start_rate_per_hour: float
    estimated_clear_minutes: float | None
    forecast_reason: ForecastReason | None


class ParkingMetrics(DemoMetadata):
    parking_duration: ParkingDurationMetric
    queues: list[QueueMetric]


@dataclass(frozen=True, slots=True)
class ParkingSession:
    session_id: str
    vehicle_id: str
    entered_at: datetime
    exited_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class QueueTicket:
    ticket_id: str
    queue_id: str
    service_type: str
    vehicle_id: str
    queue_joined_at: datetime
    service_started_at: datetime | None = None
    cancelled_at: datetime | None = None
    factory_id: str = DEMO_FACTORY


@dataclass(frozen=True, slots=True)
class QueueEvent:
    event_id: str
    event_type: Literal["queue_join", "service_start"]
    queue_id: str
    service_type: str
    vehicle_id: str
    occurred_at: datetime
    factory_id: str = DEMO_FACTORY


@dataclass(frozen=True, slots=True)
class DemoSnapshot:
    data_as_of: datetime
    coverage_start: datetime
    coverage_end: datetime
    parking_sessions: tuple[ParkingSession, ...]
    queue_tickets: tuple[QueueTicket, ...]
    queue_events: tuple[QueueEvent, ...]


def _fixture() -> DemoSnapshot:
    as_of = SNAPSHOT_AS_OF
    sessions = [ParkingSession(f"park-{i}", f"vehicle-{i}", as_of - timedelta(hours=2)) for i in range(14)]
    sessions.extend(
        [
            ParkingSession("done-1", "vehicle-done-1", as_of - timedelta(minutes=45), as_of - timedelta(minutes=25)),
            ParkingSession("done-2", "vehicle-done-2", as_of - timedelta(minutes=80), as_of - timedelta(minutes=45)),
        ]
    )
    tickets: list[QueueTicket] = []
    events: list[QueueEvent] = []
    for i in range(10):
        joined = as_of - timedelta(minutes=120 + i)
        started = as_of - timedelta(minutes=55 - i * 5)
        vehicle = f"served-{i}"
        tickets.append(QueueTicket(f"served-ticket-{i}", "loading", "loading", vehicle, joined, started))
        events.extend(
            [
                QueueEvent(f"join-served-{i}", "queue_join", "loading", "loading", vehicle, joined),
                QueueEvent(f"start-served-{i}", "service_start", "loading", "loading", vehicle, started),
            ]
        )
    for i in range(12):
        joined = as_of - timedelta(minutes=90) if i < 8 else as_of - timedelta(minutes=45 - (i - 8) * 10)
        vehicle = f"waiting-{i}"
        tickets.append(QueueTicket(f"waiting-ticket-{i}", "loading", "loading", vehicle, joined))
        events.append(QueueEvent(f"join-waiting-{i}", "queue_join", "loading", "loading", vehicle, joined))
    for queue_id, service_type, count in (("unloading", "unloading", 3), ("other", "other", 0)):
        for i in range(count):
            tickets.append(
                QueueTicket(
                    f"{queue_id}-waiting-{i}", queue_id, service_type, f"{queue_id}-vehicle-{i}",
                    as_of - timedelta(minutes=20),
                )
            )
    return DemoSnapshot(
        data_as_of=as_of,
        coverage_start=as_of - timedelta(hours=24),
        coverage_end=as_of,
        parking_sessions=tuple(sessions),
        queue_tickets=tuple(tickets),
        queue_events=tuple(events),
    )


DEFAULT_SNAPSHOT = _fixture()


def _aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


def _utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


class DemoDataAdapter:
    def __init__(self, demo_now: datetime, snapshot: DemoSnapshot = DEFAULT_SNAPSHOT) -> None:
        if not _aware(demo_now) or not _aware(snapshot.data_as_of):
            raise ValueError("demo_now va data_as_of timezone-aware bo‘lishi kerak")
        self.demo_now = _utc(demo_now)
        self.snapshot = snapshot

    @property
    def data_as_of(self) -> datetime:
        return _utc(self.snapshot.data_as_of)

    @property
    def freshness(self) -> Literal["fresh", "stale", "future"]:
        age = (self.demo_now - self.data_as_of).total_seconds()
        if age < 0:
            return "future"
        return "stale" if age > 300 else "fresh"

    def _base(self) -> DemoMetadata:
        return {
            "mode": "demo",
            "source": "demo_snapshot",
            "demo_notice": DEMO_NOTICE,
            "demo_now": self.demo_now,
            "data_as_of": self.data_as_of,
            "freshness": self.freshness,
        }

    def parking_status(self) -> ParkingStatus:
        as_of = _utc(self.snapshot.data_as_of)
        valid_active: set[str] = set()
        excluded = 0
        seen_session_ids: set[str] = set()
        for session in self.snapshot.parking_sessions:
            if session.session_id in seen_session_ids:
                excluded += 1
                continue
            seen_session_ids.add(session.session_id)
            if not _aware(session.entered_at) or (session.exited_at is not None and not _aware(session.exited_at)):
                excluded += 1
                continue
            entered = _utc(session.entered_at)
            exited = _utc(session.exited_at) if session.exited_at else None
            if entered > as_of or (exited is not None and (exited < entered or exited > as_of)):
                excluded += 1
            elif exited is None and entered <= as_of:
                valid_active.add(session.vehicle_id)
        queues: list[QueueStatus] = []
        seen_ticket_ids: set[str] = set()
        invalid_ticket_ids: set[str] = set()
        for ticket in self.snapshot.queue_tickets:
            if ticket.ticket_id in seen_ticket_ids:
                invalid_ticket_ids.add(ticket.ticket_id)
                continue
            seen_ticket_ids.add(ticket.ticket_id)
            times = [ticket.queue_joined_at, ticket.service_started_at, ticket.cancelled_at]
            present = [value for value in times if value is not None]
            if (
                ticket.ticket_id in invalid_ticket_ids
                or ticket.factory_id != DEMO_FACTORY
                or ticket.queue_id not in QUEUE_TYPES
                or ticket.service_type != QUEUE_TYPES.get(ticket.queue_id)
                or (ticket.service_started_at is not None and ticket.cancelled_at is not None)
                or any(not _aware(value) for value in present)
            ):
                invalid_ticket_ids.add(ticket.ticket_id)
                continue
            joined = _utc(ticket.queue_joined_at)
            if joined > as_of or any(_utc(value) < joined or _utc(value) > as_of for value in present[1:]):
                invalid_ticket_ids.add(ticket.ticket_id)
        excluded += len(invalid_ticket_ids)
        for queue_id, service_type in QUEUE_TYPES.items():
            vehicles: set[str] = set()
            for ticket in self.snapshot.queue_tickets:
                if ticket.queue_id != queue_id or ticket.service_type != service_type or ticket.factory_id != DEMO_FACTORY:
                    continue
                if ticket.ticket_id in invalid_ticket_ids:
                    continue
                if ticket.cancelled_at is None and ticket.service_started_at is None and _aware(ticket.queue_joined_at):
                    joined = _utc(ticket.queue_joined_at)
                    if joined <= as_of:
                        vehicles.add(ticket.vehicle_id)
            queues.append({"queue_id": queue_id, "service_type": service_type, "waiting_vehicle_count": len(vehicles)})
        return {
            **self._base(),
            "active_parking_vehicle_count": len(valid_active),
            "queues": queues,
            "excluded_invalid_records": excluded,
        }

    def metrics(self) -> ParkingMetrics:
        as_of = _utc(self.snapshot.data_as_of)
        duration_start = as_of - timedelta(hours=24)
        durations: list[float] = []
        excluded_sessions = 0
        seen_sessions: set[str] = set()
        for session in self.snapshot.parking_sessions:
            if session.exited_at is None:
                continue
            if session.session_id in seen_sessions or not _aware(session.entered_at) or not _aware(session.exited_at):
                excluded_sessions += 1
                continue
            seen_sessions.add(session.session_id)
            entered, exited = _utc(session.entered_at), _utc(session.exited_at)
            if exited <= entered or exited > as_of:
                excluded_sessions += 1
            elif exited > duration_start:
                durations.append((exited - entered).total_seconds() / 60)
        duration: ParkingDurationMetric = {
            "window_start": duration_start,
            "window_end": as_of,
            "completed_sessions": len(durations),
            "excluded_sessions": excluded_sessions,
            "average_minutes": sum(durations) / len(durations) if durations else None,
        }

        window_start = as_of - timedelta(minutes=60)
        coverage_valid = (
            _aware(self.snapshot.coverage_start)
            and _aware(self.snapshot.coverage_end)
            and _utc(self.snapshot.coverage_start) <= _utc(self.snapshot.coverage_end)
        )
        coverage = (
            coverage_valid
            and _utc(self.snapshot.coverage_start) <= window_start
            and _utc(self.snapshot.coverage_end) >= as_of
        )
        waiting_by_queue = {
            row["queue_id"]: row["waiting_vehicle_count"]
            for row in self.parking_status()["queues"]
        }
        event_id_counts: dict[str, int] = {}
        for event in self.snapshot.queue_events:
            event_id_counts[event.event_id] = event_id_counts.get(event.event_id, 0) + 1
        duplicate_event_ids = {event_id for event_id, count in event_id_counts.items() if count > 1}
        queue_rows: list[QueueMetric] = []
        for queue_id, service_type in QUEUE_TYPES.items():
            related = [event for event in self.snapshot.queue_events if event.queue_id == queue_id]
            bad_process = any(event.service_type != service_type for event in related) or any(
                ticket.service_type != service_type for ticket in self.snapshot.queue_tickets if ticket.queue_id == queue_id
            )
            bad_factory = any(event.factory_id != DEMO_FACTORY for event in related)
            queue_tickets = [ticket for ticket in self.snapshot.queue_tickets if ticket.queue_id == queue_id]
            bad_factory = bad_factory or any(ticket.factory_id != DEMO_FACTORY for ticket in queue_tickets)
            ticket_ids: set[str] = set()
            invalid_ticket_ids: set[str] = set()
            for ticket in queue_tickets:
                if ticket.ticket_id in ticket_ids:
                    invalid_ticket_ids.add(ticket.ticket_id)
                    continue
                ticket_ids.add(ticket.ticket_id)
                present = [value for value in (ticket.queue_joined_at, ticket.service_started_at, ticket.cancelled_at) if value is not None]
                if (
                    ticket.factory_id != DEMO_FACTORY
                    or (ticket.service_started_at is not None and ticket.cancelled_at is not None)
                    or any(not _aware(value) for value in present)
                ) or (
                    _utc(ticket.queue_joined_at) > as_of
                    or any(_utc(value) < _utc(ticket.queue_joined_at) or _utc(value) > as_of for value in present[1:])
                ):
                    invalid_ticket_ids.add(ticket.ticket_id)
            active_ticket_vehicles = [
                ticket.vehicle_id for ticket in queue_tickets
                if ticket.service_type == service_type and ticket.factory_id == DEMO_FACTORY
                and ticket.ticket_id not in invalid_ticket_ids
                and ticket.service_started_at is None and ticket.cancelled_at is None
            ]
            duplicate_waiters = len(active_ticket_vehicles) != len(set(active_ticket_vehicles))
            duplicate_ticket_ids = len(ticket_ids) != len(queue_tickets)
            seen_events: set[str] = set()
            valid_events: list[QueueEvent] = []
            excluded_events = 0
            duplicate_ids: set[str] = set()
            for event in related:
                if event.event_id in duplicate_event_ids:
                    duplicate_ids.add(event.event_id)
                    excluded_events += 1
                    continue
                if event.event_id in seen_events:
                    duplicate_ids.add(event.event_id)
                    excluded_events += 1
                    continue
                seen_events.add(event.event_id)
                if (
                    not _aware(event.occurred_at)
                    or _utc(event.occurred_at) > as_of
                    or event.service_type != service_type
                    or event.factory_id != DEMO_FACTORY
                    or event.event_type not in {"queue_join", "service_start"}
                ):
                    excluded_events += 1
                else:
                    valid_events.append(event)
            if duplicate_ids:
                valid_events = [event for event in valid_events if event.event_id not in duplicate_ids]
            joins_by_vehicle: dict[str, list[datetime]] = {}
            for event in valid_events:
                if event.event_type == "queue_join":
                    joins_by_vehicle.setdefault(event.vehicle_id, []).append(_utc(event.occurred_at))
            unmatched_starts: set[str] = set()
            for event in sorted(valid_events, key=lambda item: _utc(item.occurred_at)):
                if event.event_type != "service_start":
                    continue
                joins = joins_by_vehicle.get(event.vehicle_id, [])
                eligible = [(joined, index) for index, joined in enumerate(joins) if joined <= _utc(event.occurred_at)]
                if eligible:
                    joins.pop(max(eligible)[1])
                else:
                    unmatched_starts.add(event.event_id)
            if unmatched_starts:
                excluded_events += len(unmatched_starts)
                valid_events = [event for event in valid_events if event.event_id not in unmatched_starts]
            arrivals = sum(
                1 for event in valid_events
                if event.event_type == "queue_join" and window_start < _utc(event.occurred_at) <= as_of
            )
            starts = sum(
                1 for event in valid_events
                if event.event_type == "service_start" and window_start < _utc(event.occurred_at) <= as_of
            )
            waiting = int(waiting_by_queue.get(queue_id, 0))
            arrival_rate = float(arrivals)
            start_rate = float(starts)
            reason: ForecastReason | None = None
            if self.freshness == "future":
                reason = "FUTURE_DATA"
            elif self.freshness == "stale":
                reason = "STALE_DATA"
            elif not coverage:
                reason = "INSUFFICIENT_HISTORY" if coverage_valid else "INCONSISTENT_DATA"
            elif bad_process:
                reason = "PROCESS_MISMATCH"
            elif bad_factory or invalid_ticket_ids or duplicate_waiters or duplicate_ticket_ids or excluded_events:
                reason = "INCONSISTENT_DATA"
            elif int(waiting) == 0:
                reason = "EMPTY_QUEUE"
            elif starts < 10:
                reason = "INSUFFICIENT_OBSERVATIONS"
            elif start_rate - arrival_rate <= 0:
                reason = "NON_POSITIVE_NET_RATE"
            estimate = (int(waiting) / (start_rate - arrival_rate)) * 60 if reason is None else None
            queue_rows.append(
                {
                    "queue_id": queue_id,
                    "service_type": service_type,
                    "window_start": window_start,
                    "window_end": as_of,
                    "coverage_start": _utc(self.snapshot.coverage_start) if _aware(self.snapshot.coverage_start) else None,
                    "coverage_end": _utc(self.snapshot.coverage_end) if _aware(self.snapshot.coverage_end) else None,
                    "waiting_vehicle_count": int(waiting),
                    "valid_arrivals": arrivals,
                    "valid_service_starts": starts,
                    "excluded_events": excluded_events,
                    "arrival_rate_per_hour": arrival_rate,
                    "service_start_rate_per_hour": start_rate,
                    "estimated_clear_minutes": estimate,
                    "forecast_reason": reason,
                }
            )
        return {**self._base(), "parking_duration": duration, "queues": queue_rows}
