from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.parking import DEMO_NOTICE, DemoDataAdapter


def make_client():
    config = Settings("", "gemini-3.5-flash-lite", False, "2026-10-10T07:00:00Z", ("http://testserver",))
    return TestClient(create_app(config, DemoDataAdapter(datetime(2026, 10, 10, 7, tzinfo=UTC))))


def test_health_capabilities_and_parking_contracts():
    with make_client() as client:
        assert client.get("/health/live").json() == {"status": "alive"}
        ready = client.get("/health/ready").json()
        assert ready["status"] == "ready" and ready["dependencies"]["gemini"] == "disabled"
        caps = client.get("/api/v1/assistant/capabilities").json()
        assert caps["real_data_enabled"] is False
        status = client.get("/api/v1/parking/status").json()
        assert status["active_parking_vehicle_count"] == 14
        assert sum(queue["waiting_vehicle_count"] for queue in status["queues"]) == 15
        assert status["demo_notice"] == DEMO_NOTICE and status["mode"] == "demo"
        metrics = client.get("/api/v1/parking/metrics").json()
        loading = next(queue for queue in metrics["queues"] if queue["queue_id"] == "loading")
        assert loading["estimated_clear_minutes"] == 120
        assert loading["forecast_reason"] is None
        assert metrics["parking_duration"]["average_minutes"] == 27.5


def test_chat_offline_faq_parking_scope_and_no_source_are_distinct():
    with make_client() as client:
        faq = client.post("/api/v1/assistant/chat", json={"message": "Navbat matritsasi qayerda?"}).json()
        parking = client.post("/api/v1/assistant/chat", json={"message": "Parkingda nechta avtomobil bor?"}).json()
        outside = client.post("/api/v1/assistant/chat", json={"message": "Bugun ob havo qanday?"}).json()
        missing = client.post("/api/v1/assistant/chat", json={"message": "123YUKda eksport tarifi qanday?"}).json()
        assert faq["source"] == "documentation" and faq["ai_status"] == "disabled"
        assert parking["source"] == "demo_snapshot" and "sinxron emas" in parking["message"]
        assert outside["scope_status"] == "out_of_scope"
        assert outside["message"] == "Men faqat 123YUK tizimi va uning funksiyalari bo‘yicha yordam bera olaman."
        assert missing["scope_status"] == "not_found"
        assert missing["message"] == "Bu ma’lumot hozircha mavjud manbalarda topilmadi."
        queue = client.post("/api/v1/assistant/chat", json={"message": "Yuklash navbati tugash prognozi"}).json()
        assert "120 daqiqa" in queue["message"]
        assert "sinxron emas" in queue["message"] and queue["source"] == "demo_snapshot"
        assert queue["answer_kind"] == "estimate"


def test_ambiguous_queue_asks_for_clarification_without_gemini():
    with make_client() as client:
        result = client.post("/api/v1/assistant/chat", json={"message": "Navbat holati qanday?"}).json()
        assert result["scope_status"] == "clarification_required"
        assert result["clarification_id"] == "queue_service_type"
        assert result["suggested_queue_ids"] == ["loading", "unloading", "other"]


def test_validation_rejects_unknown_fields_and_overlong_messages():
    with make_client() as client:
        unknown = client.post("/api/v1/assistant/chat", json={"message": "salom", "tool": "delete"})
        long = client.post("/api/v1/assistant/chat", json={"message": "a" * 2001})
        assert unknown.status_code == 422 and unknown.json()["error"]["code"] == "INVALID_REQUEST"
        assert long.status_code == 422 and long.json()["error"]["code"] == "INVALID_REQUEST"


def test_body_limit_returns_structured_413():
    with make_client() as client:
        response = client.post("/api/v1/assistant/chat", content=b"x" * 32769, headers={"content-type": "application/json"})
        assert response.status_code == 413
        assert response.json()["error"]["code"] == "REQUEST_TOO_LARGE"
        assert response.json()["mode"] == "demo"


def test_cors_is_exact_and_no_credentials_are_enabled():
    with make_client() as client:
        allowed = client.options("/api/v1/assistant/chat", headers={"origin": "http://testserver", "access-control-request-method": "POST"})
        rejected = client.options("/api/v1/assistant/chat", headers={"origin": "https://untrusted.example", "access-control-request-method": "POST"})
        assert allowed.headers.get("access-control-allow-origin") == "http://testserver"
        assert "access-control-allow-origin" not in rejected.headers


def test_chat_fixed_window_limit_is_ten_requests_per_client():
    with make_client() as client:
        statuses = [client.post("/api/v1/assistant/chat", json={"message": "salom"}).status_code for _ in range(11)]
        assert statuses[:10] == [200] * 10
        assert statuses[10] == 429
        assert client.post("/api/v1/assistant/chat", json={"message": "salom"}).json()["error"]["code"] == "RATE_LIMITED"


def test_client_cannot_override_demo_clock():
    with make_client() as client:
        ordinary = client.get("/api/v1/parking/status").json()
        attempted = client.get("/api/v1/parking/status?demo_now=2030-01-01T00:00:00Z").json()
        assert ordinary["demo_now"] == attempted["demo_now"]
        assert ordinary["data_as_of"] == attempted["data_as_of"]
