# 123YUK AI Support Agent (local demo)

This MVP adds a standalone support widget to Zavod static routes and a read-only FastAPI backend. Its parking/session data is synthetic and is **not synchronized** with the dashboard browser demo. No real 123YUK data or authentication integration is configured.

## Run locally

Python 3.13 is recommended. From the repository root:

```powershell
if (!(Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
python -m venv backend/.venv
backend/.venv/Scripts/python -m pip install -r backend/requirements.txt
$env:GEMINI_API_KEY = ''
$env:GEMINI_FREE_TIER_CONFIRMED = 'false'
backend/.venv/Scripts/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

The local `backend/.env` contains `GEMINI_API_KEY` and `GEMINI_FREE_TIER_CONFIRMED=false`; the key is empty by default and the file is Git-ignored. For Gemini, an operator must place the key in that backend file and set the free-tier confirmation to `true` only after checking the intended AI Studio project has no active billing and the current quota/model conditions still apply. That flag is operator attestation; it does not inspect billing. Requests remain disabled for any model outside the single allowlist. No paid fallback, billing change, retry or model switch exists. FAQ and parking work while Gemini is disabled. Current Google terms also allow unpaid content to be used for product improvement and human review, so the adapter sends only curated public FAQ snippets.

Open the API at `http://127.0.0.1:8000/docs`. In a second terminal, run `python scripts/serve_demo.py` from the repository root and open `http://127.0.0.1:8080/123yuk-demo/zavod/dashboard/`. This local server binds only to loopback and serves only this repository at the GitHub Pages base path. For local API tests only, set the Zavod script's `data-api-base-url` to `http://127.0.0.1:8000`; the committed HTML keeps it blank, so no visitor messages are sent anywhere.

Edit `frontend/support-agent/widget.js`, then run `node scripts/build_widget.mjs` to copy the standalone file into the Pages asset path. Run `node scripts/inject_widget.mjs` to idempotently add it to Zavod entry pages.

To run tests, install `backend/requirements-dev.txt` then run `python -m pytest backend/tests -q`. `ruff check backend` and `mypy backend/app` are the configured quality checks.

## Demo clock and source

`DEMO_NOW` defaults to the frozen `2026-10-10T07:00:00Z`. Fixture `data_as_of` is a separate constant. Advancing the demo clock never changes the snapshot or re-times its events. The sample loading queue yields 12 waiting, 4 arrivals/hour and 10 service starts/hour, or 120 forecast minutes, solely to exercise the calculation. Every demo result carries the notice that this independent backend data is not synchronized with the dashboard.

## Local container

With Docker Engine running, `docker compose up --build` starts only the API. `docker compose config --quiet` checks the Compose file without starting containers. This project has no production data adapter, user authentication or factory ACL. Do not deploy it against real users/data until an owner approves and verifies those integrations.

## Disable/rollback the widget

Run `node scripts/inject_widget.mjs --remove` to remove only the standalone script reference from Zavod HTML. The new `zavod/ai-support/widget.js` can then be removed; no existing compiled bundle is involved. Stop the local API container with `docker compose down`.

## Separate free backend demo

[`render.yaml`](render.yaml) prepares a separate Render Free service from the `feature/ai-support-agent` branch. It uses the native Python runtime, `/health/ready`, one worker, `0.0.0.0:$PORT`, synthetic fixture data, and `GEMINI_FREE_TIER_CONFIRMED=false`; no API key, database, or persistent disk is configured. Current Hobby free limits are 750 instance-hours, 5 GB outbound bandwidth, and 500 build minutes per month. The service sleeps after 15 minutes idle and may take about a minute to wake. Keep a payment method off the account to prevent usage overages from becoming charges. Hosting research, exact manual steps, and the current deployment blocker are in [`docs/FREE_DEMO_HOSTING.md`](docs/FREE_DEMO_HOSTING.md).

The `feature/ai-support-agent` branch has been published to GitHub; Render can now read its Blueprint after the repository is connected to an authorized account. The currently published GitHub Pages dashboard does not include the widget, so this setup does not modify Pages or make the widget public. After a service is manually created, the local frontend can be tested against its HTTPS API URL through runtime widget configuration; the committed HTML remains free of a deployment URL. No public hosting has been activated from this workspace.
