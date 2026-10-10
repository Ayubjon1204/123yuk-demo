# 123YUK AI Support Agent — amalga oshirish rejasi

## Baseline (tekshirilgan)

- Public repo `Ayubjon1204/123yuk-demo`, remote default branch `main`, GitHub Pages branch `main`, path `/`.
- Baseline commit: `b5f7e7c02f35c3de61cba66858b029894597b0cc`.
- Zavod: `zavod/**/*.html`, build assetlari `zavod/assets/`; JavaScript/CSS compiled. Original frontend source, backend, configured production API/database/auth topilmadi.
- Baseline `zavod/dashboard` DEMO UI brauzerda tekshirildi; sahifada demo belgisi va parking/navbat ko‘rsatkichlari bor. Ekrandagi qiymatlar browser-local seed; backend fixture’iga ko‘chirilmaydi.
- Docker CLI/Compose bor, lekin Docker engine pipe bu muhitda ishlamadi. FastAPI, Pydantic, HTTPX, pytest va pytest-asyncio Python host’da o‘rnatilgan; mypy/ruff availabilityni local tekshirish kerak.
- Implementation working branch `feature/ai-support-agent`; tree shallow checkout main baseline’dan; uncommitted changes yo‘q.

## 0-faza — shu dokumentlar (code oldidan)

**Deliverable:** oltita docs; PRD stable requirement IDs, Mermaid context/sequence, API schemas, proposed synthetic data dictionary, threat matrix, ordered task/tests.

**Verify/exit:** documented HTTP shapes match API code; every doc identifies fact vs proposed field; Mermaid and paths checked.

**Open:** production auth/data and Gemini project entitlement.

## 1-faza — minimal backend va source layer

**Deliverables:** FastAPI app, versioned routes, `Settings`, Pydantic schemas, typed interfaces, static immutable demo fixtures, JSON public FAQ, `.env.example` and `.gitignore`; `.env` absent/untracked; Dockerfile/Compose; README.

**Verify/exit:** liveness/readiness differ; API Pydantic validation/CORS/limits/errors work; demo source is explicit; no external data/database; package imports clean.

**Open:** real API/auth integration remains disabled.

## 2-faza — demo clock and deterministic calculations

**Deliverables:** `DemoDataAdapter(demo_now, snapshot)` with explicit `DEMO_NOW=2026-10-10T07:00:00Z`; immutable independent `data_as_of=2026-10-10T07:00:00Z` and typed sessions/events; parking/queue functions. Never read `datetime.now()` for adapter, event generator, freshness or test output.

**Verify/exit:** default loading fixture has 12 waiting, 4 arrivals and 10 starts in full covered window → 120 minutes; all windows `(as_of−60m, as_of]`; duration last 24h; unknown/mixed queues are not combined; status/metrics explain demo time and independent unsynced source.

**Tests:** same fixture/hour repeat equality; `demo_now` ± 1 min does not shift fixture/events; 300 s fresh, 301 s stale, `data_as_of > demo_now` future; boundary events; complete and incomplete coverage; no-wall-clock injection; `EMPTY_QUEUE`, <10 starts, zero/negative net and mixed process each null + reason.

**Open:** none for demo semantics; all metric field names are proposed adapter-level fields only.

## 3-faza — classifier, source-bounded FAQ and agent

**Deliverables:** Unicode/apostrophe normalizer, Uzbek Latin alias map, local deterministic intent classifier, no-source/scope/off-topic/clarification cases, verified public FAQ with IDs/URIs; explicit 3-tool read-only allowlist; typed-result backend renderer.

**Verify/exit:** known parking/FAQ requests call local function and never Gemini; OOS returns exactly `Men faqat 123YUK tizimi va uning funksiyalari bo‘yicha yordam bera olaman.`; supported-topic without evidence returns exactly `Bu ma’lumot hozircha mavjud manbalarda topilmadi.`; ambiguity gets safe clarification; no unverified prose/IDs can be answered.

**Tests:** canonical Uzbek/apostrophe/case synonyms, phrases, tie/near miss, OOS text and brand-prefix+OOS text, intents with no source, full queue clarification follow-up, injection, unknown tool/args/result, fake evidence. All API outcomes include request ID and correct source/answer kind.

**Open:** FAQ expansion waits for future verified manuals/source text; do not invent data.

## 4-faza — API and widget static integration

**Deliverables:** six contracted endpoints; input and envelope schemas; CORS, caps, per-worker in-memory limits; structured/redacted logs; independent Shadow DOM custom element under `frontend/support-agent/`, deterministic copy to the standalone Zavod asset, and base-path aware HTML injection; configurably empty backend URL; documented local run and rollback. The build step copies the script; no bundler or change to existing compiled bundles is required.

**Verify/exit:** widget appears once on every Zavod entry path and direct refresh, never on other apps; UI outside widget remains pixel-identical; empty/unreachable backend does not break app; no token in localStorage or built asset.

**Tests:** navigation, open/close/reset/send/Enter, safe rendering, error/timeout, shadow CSS isolation, script reinjection idempotence; HTTP direct/nested route smoke; API response errors and CORS.

**Open:** real remote HTTPS backend URL unknown; leave empty safely. User must choose to enable on published site by merging/publishing a reviewed branch.

## 5-faza — gated Gemini adapter

**Deliverables:** isolated `GeminiAdapter` HTTPX, exact `gemini-3.5-flash-lite` allowlist/default, private `.env` key, free-tier attestation config default false, 15 s timeout, output-token bound, enum error mapper.

**Verify/exit:** operator-controlled and disabled when false/empty/unverified/unallowlisted. Exact answer built from existing locally verified article/tool result. No user text/history/tool data/credentials in request. Bounded quota/429 and timeout degrade only to actual local found evidence; otherwise return user-facing no-source message. No LLM fallback, retry or paid path.

**Tests:** request capture zero calls in default-disabled branch and on unrecognized/no-need/question data; provider body/headers contain only intent, allowlisted article IDs/approved public snippets; sensitive sentinel not present; selection subset check; timeout/429/invalid schema/missing key/provider error; API local FAQ & metrics with adapter disabled.

**Open:** provider manual smoke test requires operator-controlled key and a verifiably unbilled Google AI Studio project. No test may turn billing on.

## 6-faza — final verification/report

Run all `pytest`, `ruff check backend`, `mypy backend`, widget/Playwright and available Docker compose/config checks. Report each command and exact pass/fail/blocked result; a tool availability/engine blocker is not a test pass. Review `git diff --check`, status/diff and confirm no `.env`, secrets or unrelated app/bundle changes. Production deployment deliberately omitted.

## Operational rollback

Revert widget `<script>` references and remove only generated `zavod/ai-support/` static asset if local deployment must be disabled. Stop local Compose. Never overwrite published Pages or interact with production during this task.
