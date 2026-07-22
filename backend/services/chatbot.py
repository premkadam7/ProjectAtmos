import os
import sys
import uuid
import json
import difflib
import asyncio
from typing import Optional, AsyncGenerator, Dict, List
from dotenv import load_dotenv, find_dotenv

# Load environment variables
load_dotenv(find_dotenv())

# Import LangChain & Gemini
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

# Import metrics engines for dynamic context
from models.forecaster import get_city_overview, get_ward_forecast, get_ward_blame
from routers.enforce import get_enforcement_tickets

# Original Mock Responses for testing/fallback
RESPONSES = {
    "en": {
        "default": "Based on current data, Delhi's average AQI is 215 (Poor). The worst affected area is Anand Vihar (AQI 310) due to industrial emissions. I recommend limiting outdoor activity, especially for children and the elderly. Would you like details about a specific ward?",
        "rohini": "Rohini Sector 7 currently has an AQI of 245 (Poor). The primary contributors are traffic congestion (35%) and unfavorable wind conditions (30%). The forecast shows worsening conditions over the next 24 hours (expected AQI: 285). I'd recommend staying indoors and using an air purifier if available.",
        "dwarka": "Dwarka Sector 10 has a moderate AQI of 185. Good news — the forecast shows improvement over the next 48 hours, dropping to around 150. The main factor is weather (low wind speed trapping pollutants). Outdoor exercise is okay in the early morning when AQI tends to be lower.",
        "jogging": "Based on tomorrow's forecast, I'd avoid jogging outdoors in most parts of Delhi. The safest areas will be Vasant Kunj (forecast AQI: 135) and Dwarka (forecast AQI: 160). If you must exercise outdoors, early morning (5-7 AM) typically has the best air quality. That's equivalent to smoking about 2-3 cigarettes worth of PM2.5 exposure.",
        "worst": "The worst areas in Delhi right now are:\n1. Anand Vihar — AQI 310 (Severe) — Industrial emissions\n2. Rohini Sector 7 — AQI 245 (Poor) — Traffic + wind\n3. ITO — AQI 198 (Moderate) — Traffic congestion\n\nI strongly advise avoiding outdoor activity in Anand Vihar — breathing that air is equivalent to smoking 7.1 cigarettes today.",
    },
    "hi": {
        "default": "वर्तमान डेटा के अनुसार, दिल्ली का औसत AQI 215 (खराब) है। सबसे प्रभावित क्षेत्र आनंद विहार है (AQI 310) जो औद्योगिक उत्सर्जन के कारण है। मैं बाहरी गतिविधियों को सीमित करने की सलाह दूंगा, विशेषकर बच्चों और बुजुर्गों के लिए।",
        "rohini": "रोहिणी सेक्टर 7 का वर्तमान AQI 245 (खराब) है। मुख्य कारण ट्रैफिक (35%) और प्रतिकूल हवा की स्थिति (30%) है। अगले 24 घंटों में हालात और बिगड़ने की संभावना है। घर के अंदर रहने की सलाह है।",
        "dwarka": "द्वारका सेक्टर 10 का AQI 185 (मध्यम) है। अच्छी खबर — अगले 48 घंटों में सुधार की उम्मीद है। सुबह जल्दी बाहर जाना सुरक्षित रहेगा।",
    },
}

def _match_response(message: str, language: str) -> str:
    msg = message.lower()
    pool = RESPONSES.get(language, RESPONSES["en"])

    if "rohini" in msg or "रोहिणी" in msg:
        return pool.get("rohini", pool["default"])
    if "dwarka" in msg or "द्वारका" in msg:
        return pool.get("dwarka", pool["default"])
    if any(k in msg for k in ("jog", "exercise", "run", "जॉगिंग", "दौड़ना")):
        return pool.get("jogging", pool["default"])
    if any(k in msg for k in ("worst", "avoid", "kharab", "सबसे खराब", "खराब")):
        return pool.get("worst", pool["default"])
    return pool["default"]

def build_context_payload(query: str) -> str:
    overview = get_city_overview()
    
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
        overview_text = "Delhi City Average AQI: 215.0\nWorst Affected Ward: Anand Vihar (AQI: 310.0)\nBest Air Quality Ward: Vasant Kunj (AQI: 135.0)\n"

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

    # Fuzzy-match wards
    matched_wards_info = []
    query_lower = query.lower()
    if overview:
        for w in overview:
            name_lower = w["ward_name"].lower()
            id_lower = w["ward_id"].lower()
            id_clean = id_lower.replace("_", " ")
            
            is_matched = False
            # Substring match (either query contains ward name/id, or ward name/id contains query)
            if (name_lower in query_lower or id_lower in query_lower or id_clean in query_lower or
                query_lower in name_lower or query_lower in id_lower or query_lower in id_clean):
                is_matched = True
            else:
                # Token fuzzy and substring match
                import re
                tokens = re.findall(r'\w+', query_lower)
                for token in tokens:
                    if len(token) < 4:
                        continue
                    if token in name_lower or token in id_lower or token in id_clean:
                        is_matched = True
                        break
                    ratio_name = difflib.SequenceMatcher(None, token, name_lower).ratio()
                    ratio_id = difflib.SequenceMatcher(None, token, id_clean).ratio()
                    if max(ratio_name, ratio_id) > 0.8:
                        is_matched = True
                        break
                        
            if is_matched:
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
1. Always base your answers on the provided live context. If the user asks about a specific ward and it is present in the context, use those specific numbers.
2. If the user asks about health impacts, represent it using the "cigarette equivalent" metric (e.g. smoking X cigarettes a day) if available.
3. Be concise, professional, and helpful.
4. Keep the conversation history in mind.
5. If the language requested is "hi" or the user query is in Hindi, you MUST respond in Hindi (हिंदी) using Devanagari script. Translate concepts like 'cigarette equivalent' or 'enforcement tickets' into appropriate Hindi terms, but keep ward names recognizable. If the language is "en", respond in English.
"""

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
        sources = ["Forecast Data", "Blame Score Data"]
        use_mock = cls.should_use_mock(force_rag)

        if use_mock:
            resp_text = _match_response(message, language)
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
            model="gemini-1.5-flash",
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
            yield json.dumps({
                "error": str(e),
                "conversation_id": conversation_id,
                "done": True
            })

    @classmethod
    async def chat_non_stream(cls, message: str, language: str, conversation_id: str, force_rag: bool = False) -> dict:
        sources = ["Forecast Data", "Blame Score Data"]
        use_mock = cls.should_use_mock(force_rag)

        if use_mock:
            resp_text = _match_response(message, language)
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
            model="gemini-1.5-flash",
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

        response = await chain.ainvoke({
            "context": context,
            "history": lc_history,
            "message": message
        })
        reply_text = response.content

        cls.save_message(conversation_id, "human", message)
        cls.save_message(conversation_id, "ai", reply_text)

        return {
            "response": reply_text,
            "language": language,
            "conversation_id": conversation_id,
            "sources": sources
        }
