# 123YUK AI Support Agent — API contract (v1)

Status: these routes are **proposed and are implemented only after this contract is added**. No backend was present in the inspected repository. All JSON fields use snake_case. Every application response is UTF-8; error envelope is uniform.

## Conventions

- `Content-Type: application/json` on request/response bodies. All UTC timestamp fields are ISO-8601 RFC3339 strings ending `Z`.
- `/health/live` and `/health/ready` are service/operations endpoints; `/api/v1/...` stays versioned. Production data is disabled in this MVP.
- Browser CORS origins come only from `CORS_ALLOWED_ORIGINS`, default empty except localhost documented in local `.env`.
- Client identity, role and factory ID do not authorize access. Demo factory is constant, fixture-owned. Never accept model/user-selected tenant IDs for production lookups.
- Chat sends a single current message and up to 12 prior turns only to this backend. History roles only `user|assistant`, each content max 2,000 code points, request total max 32 KiB. History is untrusted and is never sent to Gemini.
- Requests validated with `extra="forbid"`; malformed input returns structured 422. Rate limited request returns structured 429.

## Provenance, mode and reason enums

```json
{"mode":"demo","source":"demo_snapshot","demo_notice":"Bu alohida backend demo ma’lumoti; haqiqiy dashboard bilan sinxron emas.","demo_now":"2026-10-10T07:00:00Z","data_as_of":"2026-10-10T07:00:00Z"}
```

Every data-backed demo answer includes mode/source/notice plus relevant timestamp/window/sample. Documentation answers identify `source="documentation"` with at least one verified `evidence` item; the notice appears as the current demo backend mode in the response envelope, never as a claim that documentary text is a demo fact. Error/scope responses also include `mode="demo"`, `request_id` and empty evidence. Provenance enums: `mode: demo`; `source: demo_snapshot|documentation|none`; `answer_kind: fact|estimate|instruction|unavailable`.

Forecast reason: `null` for success; otherwise one of `EMPTY_QUEUE`, `FUTURE_DATA`, `STALE_DATA`, `INSUFFICIENT_HISTORY`, `INSUFFICIENT_OBSERVATIONS`, `NON_POSITIVE_NET_RATE`, `PROCESS_MISMATCH`, `INCONSISTENT_DATA`.

## `GET /health/live`

Pure process liveness; no network/provider calls.

`200 {"status":"alive"}`. `503` only if service is shutting down/failed. Never claims data freshness or AI availability.

## `GET /health/ready`

`200 {"status":"ready","mode":"demo","dependencies":{"demo_data":"ready","faq":"ready","gemini":"disabled"}}`. `gemini` values: `disabled`, `not_configured`, `configured`, `unavailable`. Readiness is true while Gemini is missing/unavailable if required local services load. `503` if required FAQ/adapter configuration cannot load, error format below.

## `GET /api/v1/parking/status`

No query params or client `demo_now`.

```json
{
  "mode":"demo", "source":"demo_snapshot",
  "demo_notice":"Bu alohida backend demo ma’lumoti; haqiqiy dashboard bilan sinxron emas.",
  "demo_now":"2026-10-10T07:00:00Z", "data_as_of":"2026-10-10T07:00:00Z",
  "freshness":"fresh", "active_parking_vehicle_count":14,
  "queues":[
    {"queue_id":"loading","service_type":"loading","waiting_vehicle_count":12},
    {"queue_id":"unloading","service_type":"unloading","waiting_vehicle_count":3},
    {"queue_id":"other","service_type":"other","waiting_vehicle_count":0}
  ],
  "excluded_invalid_records":0, "request_id":"uuid"
}
```

`active_parking_vehicle_count` and each queue’s waiting count are distinct counts, not components of a combined total. `freshness=stale` is explicit when older than 300 s; no count is called live.

## `GET /api/v1/parking/metrics`

No query params; per-queue details, no cross-queue aggregate rate/estimate. Parking completed duration is reported separately.

```json
{
 "mode":"demo","source":"demo_snapshot",
 "demo_notice":"Bu alohida backend demo ma’lumoti; haqiqiy dashboard bilan sinxron emas.",
 "demo_now":"2026-10-10T07:00:00Z","data_as_of":"2026-10-10T07:00:00Z",
 "freshness":"fresh",
 "parking_duration":{"window_start":"2026-10-09T07:00:00Z","window_end":"2026-10-10T07:00:00Z","completed_sessions":2,"excluded_sessions":0,"average_minutes":27.5},
 "queues":[{
   "queue_id":"loading","service_type":"loading","window_start":"2026-10-10T06:00:00Z","window_end":"2026-10-10T07:00:00Z",
   "coverage_start":"2026-10-09T07:00:00Z","coverage_end":"2026-10-10T07:00:00Z",
   "waiting_vehicle_count":12,"valid_arrivals":4,"valid_service_starts":10,"excluded_events":0,
   "arrival_rate_per_hour":4.0,"service_start_rate_per_hour":10.0,
   "estimated_clear_minutes":120.0,"forecast_reason":null
 }],"request_id":"uuid"
}
```

`estimated_clear_minutes` is a forecast from the snapshot instant, not operational promise/current live guarantee. Return `null` and a declared reason for stale/future/invalid/incomplete/insufficient/non-positive snapshots. Empty queue is an already observed zero-wait state, `EMPTY_QUEUE`, forecast `null`. Demo default loading fixture: waiting=12, 60m arrivals=4, starts=10 → `(12/(10-4))*60=120min`.

## `POST /api/v1/assistant/chat`

```json
{"message":"Parkingda nechta mashina bor?","history":[]}
```

`message`: trimmed 1..2000 chars. `history`: default empty, 0..12 items, strict role enum `user|assistant`, text 1..2000. Total body max 32768 bytes. No role, user ID, factory ID, tool, prompt, model, provider, context token or clock fields allowed. History can resolve a local clarification only; it cannot supply evidence/permissions and is not forwarded to any provider.

`200` (including scope rejection, clarification, unavailable info and no-source state):

```json
{
 "message":"Bu alohida backend demo ma’lumoti; haqiqiy dashboard bilan sinxron emas. Parkingda 14 ta demo avtomobil bor (snapshot: 2026-10-10 12:00, Asia/Tashkent).",
 "answer_kind":"fact","scope_status":"in_scope","ai_status":"disabled",
 "mode":"demo","source":"demo_snapshot",
 "demo_notice":"Bu alohida backend demo ma’lumoti; haqiqiy dashboard bilan sinxron emas.",
 "demo_now":"2026-10-10T07:00:00Z","data_as_of":"2026-10-10T07:00:00Z",
 "freshness":"fresh",
 "evidence":[{"id":"parking_status","source":"demo_snapshot"}],
 "clarification_id":null,"suggested_queue_ids":[],"request_id":"uuid"
}
```

`scope_status`: `in_scope|out_of_scope|clarification_required|not_found`; `ai_status`: `disabled|not_configured|configured|unavailable|quota_exceeded|timeout|provider_error`; `source`: `demo_snapshot|documentation|none`; no raw Gemini text returned. `clarification_id` only known enum, e.g. `queue_service_type`, if safe user clarification is needed. Suggested IDs are constant backend known IDs (`loading`,`unloading`,`other`) and not trusted as auth. `evidence` records only sources that actually exist. Exact messages:

Successful queue-clearance results use `answer_kind="estimate"`; a null estimate uses `answer_kind="unavailable"` and includes its reason code in the message and metrics response.

| Outcome | `message` |
|---|---|
| OOS | `Men faqat 123YUK tizimi va uning funksiyalari bo‘yicha yordam bera olaman.` |
| in-scope no source/result | `Bu ma’lumot hozircha mavjud manbalarda topilmadi.` |
| ambiguous | Constant, direct clarifying question; no facts asserted |
| Gemini free-tier quota reached | `ai_status=quota_exceeded`; local FAQ remains usable, and an unresolved multi-candidate FAQ asks for clarification rather than guessing |
| Gemini disabled/missing/timeout | Precise machine `ai_status` is returned; deterministic FAQ/parking remains available, and unresolved FAQ selection asks for clarification |

## `GET /api/v1/assistant/capabilities`

`200`: supported static intents/tools, queue IDs, `{mode:"demo",gemini:{enabled:false,model:"gemini-3.5-flash-lite",status:"disabled"},real_data_enabled:false}`. Never emit credentials or fabricate a claim that a key is entitled to the free tier.

## Error envelope

```json
{"error":{"code":"INVALID_REQUEST","message":"So‘rov qiymatlarini tekshiring."},"mode":"demo","request_id":"uuid"}
```

HTTP map: `422 INVALID_REQUEST` (invalid Pydantic/body); `413 REQUEST_TOO_LARGE`; `429 RATE_LIMITED`; `503 INTERNAL_ERROR` for unavailable mandatory local service; `500 INTERNAL_ERROR`. Provider timeout/quota/key errors are normal typed `200` assistant responses and never 500, with local FAQ/metric fallback. No stack trace, user input, provider body or secrets in error/logs.
