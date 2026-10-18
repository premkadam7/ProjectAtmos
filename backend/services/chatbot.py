import os
import sys
import uuid
import json
import difflib
import asyncio
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional, AsyncGenerator, Dict, List
from dotenv import load_dotenv, find_dotenv

# Load environment variables
load_dotenv(find_dotenv())

# Gemini model used for RAG responses (override with GEMINI_MODEL)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Import LangChain & Gemini
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

# Import metrics engines for dynamic context
from models.forecaster import get_city_hourly, get_city_overview, get_data_source, get_ward_forecast, get_ward_blame
from routers.enforce import get_enforcement_tickets

IST = ZoneInfo("Asia/Kolkata")

BAND_NAMES = {
    "en": ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"],
    "hi": ["अच्छा", "संतोषजनक", "मध्यम", "खराब", "बहुत खराब", "गंभीर"],
}
BAND_LIMITS = [50, 100, 200, 300, 400]


def _band(aqi: float, lang: str) -> str:
    names = BAND_NAMES.get(lang, BAND_NAMES["en"])
    for i, limit in enumerate(BAND_LIMITS):
        if aqi <= limit:
            return names[i]
    return names[-1]


def _ist(iso: str) -> str:
    return datetime.fromisoformat(iso).astimezone(IST).strftime("%d %b %Y, %I:%M %p IST")


# Words that appear in ward ids/names but don't identify a ward in a question
_GENERIC_TOKENS = {"delhi", "ward", "wards", "charge", "sector", "road", "nagar", "vihar", "today", "average",
                   "quality", "tomorrow", "forecast", "pollution", "where", "which", "what", "about"}


def _match_wards(query: str, overview: list) -> list:
    """Wards whose name or id appears (exactly or fuzzily) in the query."""
    matched = []
    query_lower = query.lower()
    tokens = [t for t in re.findall(r"\w+", query_lower) if t not in _GENERIC_TOKENS]
    for w in overview:
        name_lower = w["ward_name"].lower()
        id_lower = w["ward_id"].lower()
        id_clean = id_lower.replace("_", " ")
        if (name_lower in query_lower or id_lower in query_lower or id_clean in query_lower or
                query_lower in name_lower or query_lower in id_lower or query_lower in id_clean):
            matched.append(w)
            continue
        for token in tokens:
            if len(token) < 4:
                continue
            if token in name_lower or token in id_lower or token in id_clean:
                matched.append(w)
                break
            ratio_name = difflib.SequenceMatcher(None, token, name_lower).ratio()
            ratio_id = difflib.SequenceMatcher(None, token, id_clean).ratio()
            if max(ratio_name, ratio_id) > 0.8:
                matched.append(w)
                break
    return matched


def _provenance(meta: dict) -> str:
    """One block stating where the numbers come from and how current they are."""
    fresh = meta["freshness"]
    lines = [
        f"Data source: {meta['source_detail']} (status: {meta['data_source']}).",
        f"Observed at: {_ist(meta['observed_at'])}; freshness: {fresh['status']}"
        f" (data age {fresh['data_age_minutes']} minutes).",
    ]
    if fresh["status"] == "sample":
        lines.append("WARNING: this is bundled sample data from the past, NOT current conditions.")
    elif fresh["status"] == "stale":
        lines.append("WARNING: live updates are failing; these values are out of date.")
    return "\n".join(lines)


def _sources(meta: dict) -> list:
    return [f"Atmos forecast snapshot: {meta['source_detail']} ({meta['freshness']['status']})"]


def grounded_reply(message: str, language: str, reason: str) -> str:
    """Deterministic answer built only from the current snapshot (no LLM).

    Used when Gemini is not configured or fails, so the assistant never
    presents invented readings as current facts.
    """
    lang = "hi" if language == "hi" else "en"
    overview = get_city_overview()
    meta = get_data_source()
    fresh = meta["freshness"]
    if not overview:
        return ("अभी वायु गुणवत्ता डेटा उपलब्ध नहीं है।" if lang == "hi"
                else "Air-quality data is not available right now.")

    msg = message.lower()
    lines = []
    matched = _match_wards(message, overview)[:3]
    if matched:
        for w in matched:
            if lang == "hi":
                lines.append(
                    f"{w['ward_name']}: वर्तमान AQI {w['current_aqi']:.0f} ({_band(w['current_aqi'], lang)}); "
                    f"24 घंटे बाद अनुमानित AQI {w['forecast_aqi_24h']:.0f} ({_band(w['forecast_aqi_24h'], lang)})।"
                )
            else:
                lines.append(
                    f"{w['ward_name']}: current AQI {w['current_aqi']:.0f} ({_band(w['current_aqi'], lang)}); "
                    f"predicted AQI in 24 hours {w['forecast_aqi_24h']:.0f} ({_band(w['forecast_aqi_24h'], lang)})."
                )
    elif any(k in msg for k in ("jog", "exercise", "run", "outdoor", "जॉगिंग", "दौड़", "व्यायाम")):
        timeline = get_city_hourly()
        ids = list(timeline["wards"])
        hourly = [sum(timeline["wards"][i][h] for i in ids) / len(ids) for h in range(min(24, len(timeline["timestamps"])))]
        lo = min(range(len(hourly)), key=hourly.__getitem__)
        hi_ = max(range(len(hourly)), key=hourly.__getitem__)
        if lang == "hi":
            lines.append(
                f"अगले 24 घंटों में शहर का सबसे कम अनुमानित औसत AQI {hourly[lo]:.0f} ({_band(hourly[lo], lang)}) "
                f"लगभग {_ist(timeline['timestamps'][lo])} पर, और सबसे अधिक {hourly[hi_]:.0f} "
                f"लगभग {_ist(timeline['timestamps'][hi_])} पर है। यह मॉडल का पूर्वानुमान है, गारंटी नहीं।"
            )
        else:
            lines.append(
                f"Over the next 24 hours the lowest predicted city-average AQI is {hourly[lo]:.0f} "
                f"({_band(hourly[lo], lang)}) around {_ist(timeline['timestamps'][lo])}, and the highest is "
                f"{hourly[hi_]:.0f} around {_ist(timeline['timestamps'][hi_])}. This is a model forecast, not a guarantee."
            )
    else:
        avg = sum(w["current_aqi"] for w in overview) / len(overview)
        ranked = sorted(overview, key=lambda w: w["current_aqi"], reverse=True)
        top = ", ".join(f"{w['ward_name']} ({w['current_aqi']:.0f})" for w in ranked[:3])
        best = ranked[-1]
        if lang == "hi":
            lines.append(f"दिल्ली का औसत AQI {avg:.0f} ({_band(avg, lang)}) है।")
            lines.append(f"सबसे अधिक AQI: {top}। सबसे कम: {best['ward_name']} ({best['current_aqi']:.0f})।")
        else:
            lines.append(f"Delhi's average AQI is {avg:.0f} ({_band(avg, lang)}).")
            lines.append(f"Highest AQI: {top}. Lowest: {best['ward_name']} ({best['current_aqi']:.0f}).")

    observed = _ist(meta["observed_at"])
    if lang == "hi":
        head = ("AI सहायक कॉन्फ़िगर नहीं है; यह डेटा का स्वचालित सारांश है।" if reason == "not_configured"
                else "AI सहायक अभी उपलब्ध नहीं है; यह डेटा का स्वचालित सारांश है।")
        tail = f"स्रोत: {meta['source_detail']}; अवलोकन समय {observed}।"
        if fresh["status"] == "sample":
            tail += " ध्यान दें: यह पुराना नमूना डेटा है, वर्तमान स्थिति नहीं।"
        elif fresh["status"] == "stale":
            tail += f" ध्यान दें: लाइव अपडेट विफल हो रहे हैं; डेटा {fresh['data_age_minutes'] // 60} घंटे पुराना है।"
    else:
        head = ("Automated data summary (the AI assistant is not configured)." if reason == "not_configured"
                else "The AI assistant is unavailable right now. Automated data summary:")
        tail = f"Source: {meta['source_detail']}; observed {observed}."
        if fresh["status"] == "sample":
            tail += " Note: this is past sample data, not current conditions."
        elif fresh["status"] == "stale":
            tail += f" Note: live updates are failing; this data is {fresh['data_age_minutes'] // 60} hours old."
    return "\n".join([head, *lines, tail])


def build_context_payload(query: str) -> str:
    overview = get_city_overview()
    meta = get_data_source()

    if overview:
        city_avg_aqi = sum(w["current_aqi"] for w in overview) / len(overview)
        worst_ward = max(overview, key=lambda w: w["current_aqi"])
        best_ward = min(overview, key=lambda w: w["current_aqi"])
        overview_text = (
            f"Delhi City Average AQI: {city_avg_aqi:.1f}\n"
            f"Worst Affected Ward: {worst_ward['ward_name']} (AQI: {worst_ward['current_aqi']:.1f})\n"
            f"Best Air Quality Ward: {best_ward['ward_name']} (AQI: {best_ward['current_aqi']:.1f})\n"
        )
    else:
        overview_text = "No forecast data is available.\n"

    try:
        tickets_resp = get_enforcement_tickets("delhi", source=None)
        tickets_list = tickets_resp.get("tickets", [])
        tickets_text = ""
        for t in tickets_list:
            tickets_text += f"- Ticket {t['ticket_id']} for {t['ward_name']}: Urgency: {t['urgency']}, Current AQI: {t['current_aqi']}, Recommended Action: {t['recommended_action']}\n"
    except Exception:
        tickets_text = ""

    if not tickets_text:
        tickets_text = "No active enforcement tickets.\n"

    matched_wards_info = []
    for w in _match_wards(query, overview or []):
        ward_id = w["ward_id"]
        forecast = get_ward_forecast(ward_id, hours=24)
        blame = get_ward_blame(ward_id)

        ward_text = f"Ward: {w['ward_name']} (ID: {ward_id})\n"
        if forecast:
            ward_text += f"  - Current AQI: {forecast.get('current_aqi')} (equivalent to smoking {forecast.get('cigarette_equivalent')} cigarettes/day)\n"
            hourly = forecast.get("hourly", [])
            if hourly:
                ward_text += f"  - 24h Forecast AQI: {hourly[-1]['aqi']}\n"
        if blame:
            ward_text += f"  - Primary Source: {blame.get('explanation')}\n"
            factors_str = ", ".join([f"{f['name']}: {f['percentage']}% ({f['icon']})" for f in blame.get("factors", [])])
            ward_text += f"  - Factors: {factors_str}\n"
        matched_wards_info.append(ward_text)

    matched_wards_text = "\n".join(matched_wards_info) if matched_wards_info else "No specific ward matched in the query."

    payload = (
        "=== Data Provenance ===\n"
        f"{_provenance(meta)}\n\n"
        "=== Delhi City Summary ===\n"
        f"{overview_text}\n"
        "=== Active Enforcement Tickets ===\n"
        f"{tickets_text}\n"
        "=== Matched Ward Details ===\n"
        f"{matched_wards_text}\n"
    )
    return payload

SYSTEM_PROMPT = """You are the Atmos Assistant, an expert chatbot specializing in Delhi's air quality.
You have access to live air quality data, forecasts, source attribution (SHAP blame scores), and active enforcement tickets.

Use the following live context to answer the user's query:
{context}

Guidelines:
1. Always base your answers on the provided live context. If the user asks about a specific ward and it is present in the context, use those specific numbers. Never invent readings, forecasts or safe time windows that are not in the context.
2a. Mention when the data was observed. If the provenance section marks the data as sample or stale, say so clearly in your answer.
2. If the user asks about health impacts, represent it using the "cigarette equivalent" metric (e.g. smoking X cigarettes a day) if available.
3. Be concise, professional, and helpful.
4. Keep the conversation history in mind.
5. Response language: {language_instruction}
"""

SUPPORTED_LANGUAGES = {"en", "hi"}
LANGUAGE_INSTRUCTIONS = {
    "hi": ("Respond in Hindi (हिंदी) using Devanagari script, even if the user writes in English. "
           "Translate concepts like 'cigarette equivalent' or 'enforcement tickets' into appropriate Hindi terms, "
           "but keep ward names recognizable."),
    "en": "Respond in English, even if the user writes in another language.",
}


def resolve_language(language: str) -> str:
    """Supported response language; anything else is answered in English."""
    lang = (language or "").strip().lower()
    return lang if lang in SUPPORTED_LANGUAGES else "en"

class AtmosChatbotService:
    _sessions: Dict[str, List] = {}
    MAX_HISTORY = 10

    @classmethod
    def get_history(cls, conversation_id: str) -> List:
        if conversation_id not in cls._sessions:
            cls._sessions[conversation_id] = []
        return cls._sessions[conversation_id]

    @classmethod
    def save_message(cls, conversation_id: str, role: str, content: str):
        if conversation_id not in cls._sessions:
            cls._sessions[conversation_id] = []
        cls._sessions[conversation_id].append((role, content))
        # Cap at MAX_HISTORY (5 user/assistant turns)
        if len(cls._sessions[conversation_id]) > cls.MAX_HISTORY:
            cls._sessions[conversation_id] = cls._sessions[conversation_id][-cls.MAX_HISTORY:]

    @classmethod
    def is_testing_or_mocked(cls) -> bool:
        if "pytest" in sys.modules or os.getenv("TESTING") == "true":
            return True
        if LANGCHAIN_AVAILABLE:
            try:
                from unittest.mock import MagicMock
                if isinstance(ChatGoogleGenerativeAI.invoke, MagicMock):
                    return True
            except Exception:
                pass
        return False

    @classmethod
    def should_use_mock(cls, force_rag: bool = False) -> bool:
        if force_rag:
            return False
        api_key = os.getenv("GEMINI_API_KEY")
        if not LANGCHAIN_AVAILABLE:
            return True
        if not api_key or api_key == "your_gemini_api_key_here":
            return True
        return cls.is_testing_or_mocked()

    @classmethod
    async def chat_stream(cls, message: str, language: str, conversation_id: str, force_rag: bool = False) -> AsyncGenerator[str, None]:
        language = resolve_language(language)
        sources = _sources(get_data_source())
        use_mock = cls.should_use_mock(force_rag)

        if use_mock:
            resp_text = grounded_reply(message, language, reason="not_configured")
            # Stream response word by word
            words = resp_text.split(" ")
            for i, word in enumerate(words):
                chunk = (" " if i > 0 else "") + word
                yield json.dumps({
                    "text": chunk,
                    "conversation_id": conversation_id,
                    "done": False
                })
                await asyncio.sleep(0.01)
            yield json.dumps({
                "text": "",
                "conversation_id": conversation_id,
                "done": True,
                "sources": sources
            })
            # Save history for mock conversations as well
            cls.save_message(conversation_id, "human", message)
            cls.save_message(conversation_id, "ai", resp_text)
            return

        # RAG implementation
        api_key = os.getenv("GEMINI_API_KEY")
        context = build_context_payload(message)
        history = cls.get_history(conversation_id)

        llm = ChatGoogleGenerativeAI(
            model=GEMINI_MODEL,
            temperature=0.2,
            google_api_key=api_key
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{message}")
        ])

        chain = prompt | llm

        lc_history = []
        for role, content in history:
            if role == "human":
                lc_history.append(HumanMessage(content=content))
            else:
                lc_history.append(AIMessage(content=content))

        accumulated_response = []
        try:
            async for chunk in chain.astream({
                "context": context,
                "language_instruction": LANGUAGE_INSTRUCTIONS[language],
                "history": lc_history,
                "message": message
            }):
                text_chunk = chunk.content
                accumulated_response.append(text_chunk)
                yield json.dumps({
                    "text": text_chunk,
                    "conversation_id": conversation_id,
                    "done": False
                })

            full_reply = "".join(accumulated_response)
            cls.save_message(conversation_id, "human", message)
            cls.save_message(conversation_id, "ai", full_reply)

            yield json.dumps({
                "text": "",
                "conversation_id": conversation_id,
                "done": True,
                "sources": sources
            })
        except Exception as e:
            print(f"LLM streaming failed: {e}")
            if accumulated_response:
                # Part of an answer was already sent; don't splice in a second one
                yield json.dumps({"error": str(e), "conversation_id": conversation_id, "done": True})
                return
            reply_text = grounded_reply(message, language, reason="unavailable")
            cls.save_message(conversation_id, "human", message)
            cls.save_message(conversation_id, "ai", reply_text)
            yield json.dumps({"text": reply_text, "conversation_id": conversation_id, "done": False})
            yield json.dumps({"text": "", "conversation_id": conversation_id, "done": True, "sources": sources})

    @classmethod
    async def chat_non_stream(cls, message: str, language: str, conversation_id: str, force_rag: bool = False) -> dict:
        language = resolve_language(language)
        sources = _sources(get_data_source())
        use_mock = cls.should_use_mock(force_rag)

        if use_mock:
            resp_text = grounded_reply(message, language, reason="not_configured")
            cls.save_message(conversation_id, "human", message)
            cls.save_message(conversation_id, "ai", resp_text)
            return {
                "response": resp_text,
                "language": language,
                "conversation_id": conversation_id,
                "sources": sources
            }

        # RAG implementation
        api_key = os.getenv("GEMINI_API_KEY")
        context = build_context_payload(message)
        history = cls.get_history(conversation_id)

        llm = ChatGoogleGenerativeAI(
            model=GEMINI_MODEL,
            temperature=0.2,
            google_api_key=api_key
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{message}")
        ])

        chain = prompt | llm

        lc_history = []
        for role, content in history:
            if role == "human":
                lc_history.append(HumanMessage(content=content))
            else:
                lc_history.append(AIMessage(content=content))

        try:
            response = await chain.ainvoke({
                "context": context,
                "language_instruction": LANGUAGE_INSTRUCTIONS[language],
                "history": lc_history,
                "message": message
            })
            reply_text = response.content
        except Exception as e:
            # Fall back to a summary of real snapshot data (e.g. invalid key, quota exceeded)
            print(f"LLM generation failed: {e}")
            reply_text = grounded_reply(message, language, reason="unavailable")

        cls.save_message(conversation_id, "human", message)
        cls.save_message(conversation_id, "ai", reply_text)

        return {
            "response": reply_text,
            "language": language,
            "conversation_id": conversation_id,
            "sources": sources
        }
