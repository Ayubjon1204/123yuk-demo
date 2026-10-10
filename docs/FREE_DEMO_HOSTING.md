# Free demo hosting decision

Checked on 2026-10-10 against provider documentation. This is a separate synthetic demo only. No service has been created, no repository branch has been pushed, and no provider account was available in the current browser session.

## Provider comparison

| Provider | FastAPI and source support | Free terms relevant to this MVP | Decision |
|---|---|---|---|
| Render | Official FastAPI instructions use Python, Uvicorn, `0.0.0.0:$PORT`; Blueprints support Git branches and a monorepo `rootDir`. | Free web service is $0 with 750 workspace instance hours/month, 5 GB outbound bandwidth/month, and 500 build-pipeline minutes/month. Idle services sleep after 15 minutes and take about a minute to wake. Filesystem is ephemeral. Without a payment method, exceeding bandwidth suspends services until the next month; exceeding build minutes disables new builds while existing deployments keep running. With a payment method, current overages are $0.15/GB bandwidth and $5/1,000 build minutes. Inbound HTTPS/TLS is managed; the free-service docs explicitly block outbound SMTP ports 25/465/587, while actual outbound HTTPS has not yet been tested on a deployed instance. This repo needs no persistent storage. | **Selected.** No paid plan or payment method is needed for the intended free service. Leave payment details absent; stop if the dashboard requires a paid plan or payment method. |
| Koyeb | Official FastAPI guide supports Git deployment; Web Services read `PORT`. | One free web service per organization, 512 MB RAM, 0.1 vCPU, 2 GB disk; scales to zero after one hour idle. However, account validation requires a credit card and places a $29 authorization hold; the pricing FAQ says the selected plan is also charged on signup (its example is Pro). | Rejected: violates the no-payment-details/no-charge condition. |
| Railway | Official docs support deployments and offer a free tier without a card. | The free tier starts with a 30-day/$5 trial, then $1 monthly credit; unverified trial accounts may have restricted outbound networking. That makes an ongoing public E2E demo dependent on a short trial/credit regime and verification. | Rejected for this demo's predictable $0 operation. |
| Hugging Face Spaces | Docker Spaces support FastAPI and custom containers. | Current docs say CPU-basic compute Spaces (including Docker) require a PRO subscription for individual accounts; paid hardware also needs a payment method/prepaid credits. | Rejected: hosting the required app is not available on a no-subscription individual plan. |

Official sources:

- [Render free services and limits](https://render.com/docs/free), [outbound bandwidth quotas and overages](https://render.com/docs/outbound-bandwidth), [build-pipeline quotas](https://render.com/docs/build-pipeline), [FastAPI deploy](https://render.com/docs/deploy-fastapi), [Blueprint specification](https://render.com/docs/blueprint-spec), [Python version](https://render.com/docs/python-version), [environment variables and secrets](https://render.com/docs/configure-environment-variables).
- [Koyeb FastAPI deploy](https://www.koyeb.com/docs/deploy/fastapi), [free instance limits](https://www.koyeb.com/docs/reference/instances), [card verification and billing](https://www.koyeb.com/docs/faqs/pricing).
- [Railway pricing](https://railway.com/pricing), [trial and verification limits](https://docs.railway.com/pricing/free-trial).
- [Hugging Face Docker Spaces](https://huggingface.co/docs/hub/spaces-sdks-docker), [current compute/subscription requirements](https://huggingface.co/docs/huggingface_hub/guides/manage-spaces).

Render's free service remains subject to workspace-wide hours, included bandwidth/build limits, provider restarts and cold starts. A payment method can enable overage billing, so this plan deliberately does not add one. The service has a synthetic fixture, no persistent writes, no production adapter, no authentication, and Gemini remains disabled. Public availability is not guaranteed.

## Prepared backend configuration

[`../render.yaml`](../render.yaml) defines one Render Free web service on `feature/ai-support-agent`, rooted at `backend/`; the app binds to `0.0.0.0` and the provider's `$PORT`, uses one worker for the existing process-local rate limiter, and checks `/health/ready`. It pins the already-tested Python 3.13.14 runtime. The blueprint explicitly keeps `GEMINI_FREE_TIER_CONFIRMED=false` and has no `GEMINI_API_KEY` entry. The local `backend/.env` stays ignored by `backend/.gitignore` and must never be uploaded.

CORS is limited to the two local preview origins because the currently published GitHub Pages dashboard does not contain the widget. No public Pages or preview origin is enabled until a preview is actually created. The public API carries synthetic data only, but CORS is not authentication or access control.

The API needs no database, volume, queue, or other persistent service. It can be deployed using Render's native Python runtime; Docker Engine is not needed.

## Manual deployment and local-browser E2E

Provider authentication was not available, and the feature branch is not on GitHub. When an operator with an existing Render account is ready:

1. Push only this feature branch with `git push -u origin feature/ai-support-agent`; do not push or merge `main`.
2. In Render, create a Blueprint from `Ayubjon1204/123yuk-demo`, choose branch `feature/ai-support-agent`, and use the repository's `render.yaml`. Confirm the only service is the Free web service. Do not add a card, upgrade the plan, or add any database.
3. Wait for the first deploy, then record the service's assigned `https://…onrender.com` URL. Check `/health/live`, `/health/ready`, both parking endpoints, and `/api/v1/assistant/capabilities`. Readiness must show Gemini `disabled` and real-data integration off.
4. For browser testing from this local preview, run the local frontend server on port 8080. In the browser test, set `document.querySelector('yuk-support-widget').apiBase` to the verified public API origin. This is runtime test configuration; do not put a service URL or secret in the committed Pages HTML. The Render CORS list permits only `localhost:8080` and `127.0.0.1:8080` for that test.
5. Do not change the current GitHub Pages source. The published dashboard currently returns HTTP 200 but contains no widget script. The widget-enabled frontend is therefore not public. Use the local frontend against the public backend until a separate static preview can be provisioned and given its own exact CORS origin.

For rollback, suspend the separately named Render demo service in its dashboard. This does not affect GitHub Pages. If permanent removal is needed, remove only `123yuk-ai-support-demo-api` after confirming the service identity; do not change the repository's Pages settings.

## Current deployment gate

**BLOCKED:** no Render account/session is available, and `feature/ai-support-agent` has not been pushed. Therefore there is no deployed URL, public backend E2E, public-service rate-limit observation, or public browser CORS result. The local backend and UI tests remain the evidence for this checkout; they do not prove hosting behavior. Render's deployment also makes a limitation of the current rate limiter relevant: it uses the ASGI peer address and does not trust proxy-supplied `X-Forwarded-For`; a live service test must confirm whether Render presents client-specific peer addresses before the demo is shared broadly.
