import json

import httpx
import pytest

from app.assistant import (
    NOT_FOUND_REPLY,
    SCOPE_REPLY,
    Assistant,
    GeminiAdapter,
    classify,
    load_faq,
)
from app.config import Settings
from app.parking import SNAPSHOT_AS_OF, DemoDataAdapter


def settings(confirmed=False, key="", model="gemini-3.5-flash-lite"):
    return Settings(key, model, confirmed, "2026-10-10T07:00:00Z", ("http://localhost",))


def test_uzbek_synonyms_and_intents_are_local():
    assert classify("Parkovkada nechta avto bor?").code == "PARKING_STATUS"
    assert classify("Yuk ortish navbati qachon tugaydi?").code == "QUEUE_FORECAST"
    assert classify("Navbat holati").code == "CLARIFICATION_REQUIRED"
    assert classify("Navbat matritsasi qayerda?").code == "FAQ_LOOKUP"
    assert classify("Rollar haqida").clarification_id == "faq_topic"
    assert classify("Parkingda qancha?").clarification_id == "parking_metric"


@pytest.mark.asyncio
async def test_out_of_scope_and_missing_source_have_exact_distinct_replies():
    local = Assistant(DemoDataAdapter(SNAPSHOT_AS_OF), GeminiAdapter(settings()), load_faq())
    outside = await local.chat("Bugun ob havo qanday?", [])
    missing = await local.chat("123YUKda eksport jadvallarini qanday sozlayman?", [])
    assert outside["message"] == SCOPE_REPLY and outside["scope_status"] == "out_of_scope"
    assert missing["message"] == NOT_FOUND_REPLY and missing["scope_status"] == "not_found"


@pytest.mark.asyncio
async def test_faq_and_parking_work_with_gemini_unavailable():
    async def forbidden(request):
        raise AssertionError("Gemini should not be called")

    client = httpx.AsyncClient(transport=httpx.MockTransport(forbidden))
    local = Assistant(DemoDataAdapter(SNAPSHOT_AS_OF), GeminiAdapter(settings(), client), load_faq())
    faq = await local.chat("Navbat matritsasi qayerda?", [])
    roles = await local.chat("Xodimning qaysi bo‘limlarni ko‘radi?", [])
    parking = await local.chat("Parkingda nechta mashina bor?", [])
    assert faq["source"] == "documentation" and faq["evidence"][0]["id"] == "queue_matrix_navigation"
    assert roles["source"] == "documentation" and roles["evidence"][0]["id"] == "factory_role_visibility"
    assert parking["source"] == "demo_snapshot" and "sinxron emas" in parking["message"]
    assert faq["ai_status"] == "disabled"
    await client.aclose()


@pytest.mark.asyncio
async def test_gemini_outbound_has_only_intent_and_public_candidates():
    requests = []

    async def capture(request):
        requests.append(request)
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": '{"candidate_id":"factory_roles_navigation"}'}]}}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(capture))
    provider = GeminiAdapter(settings(True, "test-only-secret"), client)
    articles = [article for article in load_faq() if article.topic == "factory_roles"]
    selected, state = await provider.select_candidate("FAQ_LOOKUP", articles)
    request = requests[0]
    raw = request.content.decode()
    payload = json.loads(json.loads(request.read().decode())["contents"][0]["parts"][0]["text"])
    assert selected == "factory_roles_navigation" and state == "configured"
    assert "x-goog-api-key" in request.headers and "test-only-secret" not in str(request.url)
    assert set(payload) == {"intent_code", "candidates"}
    assert "private-marker" not in raw and "user-history-marker" not in raw
    assert all(set(item) == {"id", "snippet"} for item in payload["candidates"])
    await client.aclose()


@pytest.mark.asyncio
async def test_assistant_never_forwards_message_or_history_to_gemini():
    payloads = []

    async def capture(request):
        payload = json.loads(request.content)
        payloads.append(json.loads(payload["contents"][0]["parts"][0]["text"]))
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": '{"candidate_id":"factory_roles_navigation"}'}]}}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(capture))
    articles = load_faq()
    service = Assistant(DemoDataAdapter(SNAPSHOT_AS_OF), GeminiAdapter(settings(True, "test-key"), client), articles)
    result = await service.chat(
        "xodim roli, rollar qayerda? PRIVATE_QUERY_MARKER",
        [{"role": "user", "content": "PRIVATE_HISTORY_MARKER"}],
    )
    assert result["source"] == "documentation"
    wire = json.dumps(payloads)
    assert "PRIVATE_QUERY_MARKER" not in wire
    assert "PRIVATE_HISTORY_MARKER" not in wire
    await client.aclose()


@pytest.mark.asyncio
async def test_queue_clarification_followup_is_resolved_locally():
    service = Assistant(DemoDataAdapter(SNAPSHOT_AS_OF), GeminiAdapter(settings()), load_faq())
    result = await service.chat(
        "Boshqa xizmat",
        [
            {"role": "user", "content": "Navbat tugash prognozi qachon?"},
            {"role": "assistant", "content": "Qaysi xizmat navbati nazarda tutilgan: yuklashmi, tushirishmi yoki boshqa xizmatmi?"},
        ],
    )
    assert result["scope_status"] == "in_scope"
    assert result["source"] == "demo_snapshot"
    assert "Sabab: EMPTY_QUEUE" in result["message"]


@pytest.mark.asyncio
async def test_stale_demo_status_is_labeled_for_the_user():
    from datetime import timedelta

    service = Assistant(
        DemoDataAdapter(SNAPSHOT_AS_OF + timedelta(seconds=301)),
        GeminiAdapter(settings()),
        load_faq(),
    )
    result = await service.chat("Parkingda nechta mashina bor?", [])
    assert result["freshness"] == "stale"
    assert "Snapshot eskirgan" in result["message"]


@pytest.mark.asyncio
async def test_disabled_or_unapproved_model_makes_zero_upstream_calls():
    calls = []

    async def capture(request):
        calls.append(request)
        return httpx.Response(200, json={})

    client = httpx.AsyncClient(transport=httpx.MockTransport(capture))
    articles = [article for article in load_faq() if article.topic == "factory_roles"]
    assert await GeminiAdapter(settings(False, "secret"), client).select_candidate("FAQ_LOOKUP", articles) == (None, "disabled")
    assert await GeminiAdapter(settings(True, "secret", "gemini-unapproved"), client).select_candidate("FAQ_LOOKUP", articles) == (None, "unavailable")
    assert not calls
    await client.aclose()


@pytest.mark.asyncio
async def test_missing_key_is_distinct_and_makes_zero_upstream_calls():
    calls = []

    async def capture(request):
        calls.append(request)
        return httpx.Response(200, json={})

    client = httpx.AsyncClient(transport=httpx.MockTransport(capture))
    articles = [article for article in load_faq() if article.topic == "factory_roles"]
    provider = GeminiAdapter(settings(True), client)
    assert provider.status == "not_configured"
    assert await provider.select_candidate("FAQ_LOOKUP", articles) == (None, "not_configured")
    assert not calls
    await client.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(("response", "state"), [(httpx.Response(429), "quota_exceeded"), (httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": '{"candidate_id":"invented"}'}]}}]}), "provider_error")])
async def test_quota_and_untrusted_provider_ids_are_not_used(response, state):
    calls = []

    async def respond(request):
        calls.append(request)
        return response

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    articles = [article for article in load_faq() if article.topic == "factory_roles"]
    choice, status = await GeminiAdapter(settings(True, "secret"), client).select_candidate("FAQ_LOOKUP", articles)
    assert choice is None and status == state
    assert len(calls) == 1
    await client.aclose()


@pytest.mark.asyncio
async def test_timeout_is_a_typed_provider_state():
    async def timeout(request):
        raise httpx.ReadTimeout("private-marker")

    client = httpx.AsyncClient(transport=httpx.MockTransport(timeout))
    articles = [article for article in load_faq() if article.topic == "factory_roles"]
    assert await GeminiAdapter(settings(True, "secret"), client).select_candidate("FAQ_LOOKUP", articles) == (None, "timeout")
    await client.aclose()
