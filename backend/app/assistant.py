from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict

from .config import Settings
from .parking import DEMO_NOTICE, DemoDataAdapter

SCOPE_REPLY = "Men faqat 123YUK tizimi va uning funksiyalari bo‘yicha yordam bera olaman."
NOT_FOUND_REPLY = "Bu ma’lumot hozircha mavjud manbalarda topilmadi."
CLARIFY_QUEUE = "Qaysi xizmat navbati nazarda tutilgan: yuklashmi, tushirishmi yoki boshqa xizmatmi?"
CLARIFY_TOPIC = "123YUK bo‘yicha qaysi ma’lumot kerakligini aniqlashtirib yozing."
CLARIFY_ROLES = "Rollar haqida qaysi ma’lumot kerak: xodimlar ko‘radigan bo‘limlarmi yoki menyudagi Rollar bo‘limimi?"
CLARIFY_PARKING = "Parkingdagi avtomobillar soni kerakmi yoki o‘rtacha turish davomiyligimi?"
INTENTS = (
    "PARKING_STATUS", "PARKING_DURATION", "QUEUE_STATUS", "QUEUE_FORECAST", "FAQ_LOOKUP",
    "GREETING", "OUT_OF_SCOPE", "IN_SCOPE_NOT_FOUND", "CLARIFICATION_REQUIRED",
)
TOOLS = ("get_parking_status", "get_parking_metrics", "search_faq")
EXTERNAL_TERMS = {
    "ob havo", "weather", "futbol", "kino", "retsept", "bitcoin", "python dasturlash",
    "siyosat", "prezident", "system prompt", "maxfiy prompt",
}
SYNONYMS = {
    "parkovka": "parking", "parkovkada": "parking", "parkovkani": "parking", "turargohda": "parking",
    "mashina": "avtomobil", "mashinalar": "avtomobil", "mashinada": "avtomobil", "avto": "avtomobil",
    "avtomobillar": "avtomobil", "avtomobilni": "avtomobil",
    "yuk ortish": "yuklash", "ortish": "yuklash", "yuklashda": "yuklash", "yuklashni": "yuklash", "yuklashga": "yuklash",
    "tushirishda": "tushirish", "tushirishni": "tushirish", "tushirishga": "tushirish",
    "navbatga": "navbat", "navbatni": "navbat", "navbatda": "navbat", "navbatlar": "navbat",
    "rol": "rollar", "roli": "rollar", "rolni": "rollar", "rolga": "rollar", "rolda": "rollar", "rollarni": "rollar", "rollari": "rollar", "role": "rollar",
    "setting": "sozlamalar", "settings": "sozlamalar", "sozlamada": "sozlamalar", "sozlamalarda": "sozlamalar", "sozlama": "sozlamalar",
    "qayerda": "qayer", "kirish": "login", "zavodda": "zavod", "xodimlar": "xodim", "xodimning": "xodim",
}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower().replace("ʻ", "'").replace("ʼ", "'").replace("’", "'").replace("‘", "'")
    text = re.sub(r"[^\w\s'-]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()
    for old, new in SYNONYMS.items():
        text = re.sub(rf"\b{re.escape(old)}\b", new, text)
    return text


@dataclass(frozen=True, slots=True)
class Intent:
    code: str
    queue_id: str | None = None
    clarification_id: str | None = None


def classify(text: str) -> Intent:
    value = normalize(text)
    if not value:
        return Intent("CLARIFICATION_REQUIRED", clarification_id="question")
    if any(term in value for term in EXTERNAL_TERMS):
        return Intent("OUT_OF_SCOPE")
    if value in {"salom", "assalomu alaykum", "assalom", "rahmat", "yaxshi kun"}:
        return Intent("GREETING")
    if "navbat matritsasi" in value:
        return Intent("FAQ_LOOKUP")
    if "rollar" in value and not any(term in value for term in ("qayer", "bo'lim", "ruxsat", "xodim", "kim", "belgil", "ko'r")):
        return Intent("CLARIFICATION_REQUIRED", clarification_id="faq_topic")

    has_parking = any(term in value for term in ("parking", "avtomobil", "mashina"))
    has_queue = "navbat" in value or any(word in value for word in ("yuklash", "tushirish"))
    if has_parking and any(word in value for word in ("davomiy", "qancha vaqt", "o'rtacha vaqt", "necha minut")):
        return Intent("PARKING_DURATION")
    if has_parking and any(word in value for word in ("nechta", "soni", "avtomobil", "holat")):
        return Intent("PARKING_STATUS")
    if has_parking and "qancha" in value:
        return Intent("CLARIFICATION_REQUIRED", clarification_id="parking_metric")
    if has_parking and not has_queue:
        return Intent("PARKING_STATUS")
    if has_queue:
        queue_id = "loading" if "yuklash" in value else "unloading" if "tushirish" in value else None
        if any(word in value for word in ("prognoz", "qachon", "qancha vaqt", "necha soat", "necha daqiqa", "necha minut", "kutil", "tugaydi", "bo'shaydi", "bo'shash")):
            return Intent("QUEUE_FORECAST", queue_id, None if queue_id else "queue_service_type")
        if queue_id is None:
            return Intent("CLARIFICATION_REQUIRED", clarification_id="queue_service_type")
        return Intent("QUEUE_STATUS", queue_id)

    if any(term in value for term in ("123yuk", "zavod", "rollar", "sozlamalar", "login", "xodim", "admin")):
        return Intent("FAQ_LOOKUP")
    return Intent("OUT_OF_SCOPE")


class FAQArticle(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str
    topic: str
    title: str
    text: str
    source_uri: str
    aliases: tuple[str, ...]


def load_faq(path: Path | None = None) -> tuple[FAQArticle, ...]:
    raw = json.loads((path or Path(__file__).with_name("faq.json")).read_text(encoding="utf-8"))
    articles = tuple(FAQArticle.model_validate(item) for item in raw)
    if not articles or len({item.id for item in articles}) != len(articles):
        raise ValueError("FAQ manbalari bo‘sh yoki IDlar takrorlangan")
    return articles


def search_faq(query: str, articles: tuple[FAQArticle, ...]) -> list[FAQArticle]:
    value = normalize(query)
    exact = [article for article in articles if any(normalize(alias) in value for alias in article.aliases)]
    if exact:
        return exact
    terms = set(value.split())
    scored = [(sum(len(terms.intersection(set(normalize(alias).split()))) for alias in article.aliases), article) for article in articles]
    best = max((score for score, _ in scored), default=0)
    return [article for score, article in scored if score == best and score >= 2]


class GeminiSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidate_id: str


class GeminiAdapter:
    URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self.settings = settings
        self.client = client

    @property
    def status(self) -> str:
        return self.settings.gemini_status

    async def select_candidate(
        self, intent_code: str, candidates: list[FAQArticle]
    ) -> tuple[str | None, str]:
        if not self.settings.gemini_free_tier_confirmed:
            return None, "disabled"
        if self.settings.gemini_model != "gemini-3.5-flash-lite":
            return None, "unavailable"
        if not self.settings.gemini_api_key:
            return None, "not_configured"
        allowed = {candidate.id for candidate in candidates}
        if intent_code != "FAQ_LOOKUP" or len(candidates) < 2 or len({c.topic for c in candidates}) != 1:
            return None, "configured"
        payload = {
            "intent_code": intent_code,
            "candidates": [{"id": c.id, "snippet": c.text} for c in candidates],
        }
        body = {
            "contents": [{"role": "user", "parts": [{"text": json.dumps(payload, ensure_ascii=False)}]}],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": 32,
                "responseMimeType": "application/json",
                "responseSchema": {
                    "type": "OBJECT",
                    "properties": {"candidate_id": {"type": "STRING", "enum": sorted(allowed)}},
                    "required": ["candidate_id"],
                },
            },
        }
        own_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=httpx.Timeout(15.0))
        try:
            response = await client.post(
                self.URL.format(model=self.settings.gemini_model),
                headers={"x-goog-api-key": self.settings.gemini_api_key},
                json=body,
            )
            if response.status_code == 429:
                return None, "quota_exceeded"
            response.raise_for_status()
            candidates_out = response.json().get("candidates", [])
            text = candidates_out[0]["content"]["parts"][0]["text"]
            selected = GeminiSelection.model_validate_json(text).candidate_id
            return (selected, "configured") if selected in allowed else (None, "provider_error")
        except httpx.TimeoutException:
            return None, "timeout"
        except (httpx.HTTPError, KeyError, IndexError, ValueError):
            return None, "unavailable"
        finally:
            if own_client:
                await client.aclose()


class Assistant:
    def __init__(self, adapter: DemoDataAdapter, gemini: GeminiAdapter, articles: tuple[FAQArticle, ...]) -> None:
        self.adapter = adapter
        self.gemini = gemini
        self.articles = articles

    @property
    def ai_status(self) -> str:
        return self.gemini.status

    def _reply(self, message: str, code: str, source: str = "none", evidence: list[dict[str, str]] | None = None, **extra: Any) -> dict[str, Any]:
        return {
            "message": message,
            "answer_kind": "unavailable" if source == "none" else ("instruction" if source == "documentation" else "fact"),
            "scope_status": code,
            "ai_status": self.ai_status,
            "mode": "demo",
            "source": source,
            "demo_notice": DEMO_NOTICE,
            "demo_now": self.adapter.demo_now,
            "data_as_of": self.adapter.data_as_of if source == "demo_snapshot" else None,
            "freshness": self.adapter.freshness if source == "demo_snapshot" else None,
            "evidence": evidence or [],
            "clarification_id": None,
            "suggested_queue_ids": [],
            **extra,
        }

    async def chat(self, message: str, history: list[dict[str, str]]) -> dict[str, Any]:
        intent = classify(message)
        if history and history[-1].get("role") == "assistant" and history[-1].get("content") == CLARIFY_QUEUE:
            answer = normalize(message)
            chosen_queue = (
                "loading" if "yuklash" in answer else
                "unloading" if "tushirish" in answer else
                "other" if answer in {"boshqa", "boshqa xizmat", "other"} else None
            )
            if chosen_queue:
                previous_question = next((turn["content"] for turn in reversed(history[:-1]) if turn.get("role") == "user"), "")
                previous_intent = classify(previous_question)
                intent = Intent("QUEUE_FORECAST" if previous_intent.code == "QUEUE_FORECAST" else "QUEUE_STATUS", chosen_queue)
        if intent.code == "OUT_OF_SCOPE":
            return self._reply(SCOPE_REPLY, "out_of_scope")
        if intent.code == "CLARIFICATION_REQUIRED":
            suggestions = ["loading", "unloading", "other"] if intent.clarification_id == "queue_service_type" else []
            clarification = {
                "faq_topic": CLARIFY_ROLES,
                "parking_metric": CLARIFY_PARKING,
            }.get(intent.clarification_id or "", CLARIFY_QUEUE if suggestions else CLARIFY_TOPIC)
            return self._reply(
                clarification,
                "clarification_required",
                clarification_id=intent.clarification_id,
                suggested_queue_ids=suggestions,
            )
        if intent.code == "GREETING":
            return self._reply("Salom! 123YUK bo‘yicha parking, navbat yoki tasdiqlangan yo‘riqnomani so‘rashingiz mumkin.", "in_scope")
        freshness_note = {
            "fresh": "",
            "stale": " Snapshot eskirgan.",
            "future": " Snapshot demo soatidan kelajakda.",
        }[self.adapter.freshness]
        if intent.code == "PARKING_STATUS":
            result = self.adapter.parking_status()
            count = result["active_parking_vehicle_count"]
            return self._reply(
                f"{DEMO_NOTICE} Parkingda {count} ta demo avtomobil bor (snapshot: {result['data_as_of'].isoformat()}).{freshness_note}",
                "in_scope", "demo_snapshot", [{"id": "parking_status", "source": "demo_snapshot"}],
            )
        if intent.code in {"QUEUE_STATUS", "QUEUE_FORECAST"}:
            metrics = self.adapter.metrics()
            rows = metrics["queues"]
            row = next((item for item in rows if item["queue_id"] == intent.queue_id), None)
            if row is None:
                return self._reply(NOT_FOUND_REPLY, "not_found")
            if intent.code == "QUEUE_STATUS":
                answer = f"{DEMO_NOTICE} {intent.queue_id} navbatida {row['waiting_vehicle_count']} ta demo avtomobil kutmoqda.{freshness_note}"
            elif row["estimated_clear_minutes"] is None:
                answer = f"{DEMO_NOTICE} Navbat tugash prognozi mavjud emas. Sabab: {row['forecast_reason']}."
            else:
                answer = f"{DEMO_NOTICE} {intent.queue_id} navbatining demo prognozi {row['estimated_clear_minutes']:.0f} daqiqa."
            answer_kind = (
                "estimate" if row["estimated_clear_minutes"] is not None
                else "unavailable" if intent.code == "QUEUE_FORECAST"
                else "fact"
            )
            return self._reply(
                answer, "in_scope", "demo_snapshot", [{"id": f"queue_{intent.queue_id}", "source": "demo_snapshot"}],
                data_as_of=self.adapter.data_as_of, answer_kind=answer_kind,
            )
        if intent.code == "PARKING_DURATION":
            metric = self.adapter.metrics()["parking_duration"]
            average = metric["average_minutes"]
            answer = NOT_FOUND_REPLY if average is None else f"{DEMO_NOTICE} Demo ma’lumotlaridagi o‘rtacha parking davomiyligi {average:.1f} daqiqa.{freshness_note}"
            return self._reply(answer, "in_scope" if average is not None else "not_found", "demo_snapshot" if average is not None else "none", [{"id": "parking_duration", "source": "demo_snapshot"}] if average is not None else [])
        if intent.code == "FAQ_LOOKUP":
            candidates = search_faq(message, self.articles)
            if not candidates:
                return self._reply(NOT_FOUND_REPLY, "not_found")
            selected: FAQArticle | None = candidates[0] if len(candidates) == 1 else None
            ai_status = self.ai_status
            if len(candidates) > 1 and len({candidate.topic for candidate in candidates}) == 1:
                choice, ai_status = await self.gemini.select_candidate("FAQ_LOOKUP", candidates)
                selected = next((candidate for candidate in candidates if candidate.id == choice), None)
            if selected is None:
                return self._reply(
                    CLARIFY_TOPIC, "clarification_required", ai_status=ai_status,
                    clarification_id="faq_topic",
                )
            return self._reply(
                selected.text, "in_scope", "documentation",
                [{"id": selected.id, "source": selected.source_uri}], ai_status=ai_status,
            )
        return self._reply(NOT_FOUND_REPLY, "not_found")
