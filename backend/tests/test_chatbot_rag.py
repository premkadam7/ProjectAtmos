import pytest
import json
import sys
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from main import app
from services.chatbot import AtmosChatbotService, build_context_payload

def test_fuzzy_matching_ward():
    # Test built-in context builder fuzzy matching logic
    # Rohini
    context = build_context_payload("Why is Rohini spiking?")
    assert "Ward: Rohini" in context
    assert "Current AQI:" in context
    assert "Primary Source: AQI is primarily influenced by" in context

    # Dwarka
    context_dwarka = build_context_payload("Tell me about dwarka")
    assert "Ward: Dwarka Sector 8" in context_dwarka or "Ward: NSIT Dwarka" in context_dwarka

    # Random query shouldn't match ward details
    context_random = build_context_payload("What is the weather?")
    assert "No specific ward matched" in context_random

def test_conversation_history_pruning():
    conversation_id = "test_history_conv"
    # Ensure it's empty
    if conversation_id in AtmosChatbotService._sessions:
        del AtmosChatbotService._sessions[conversation_id]

    # Save 12 messages (6 turns)
    for i in range(12):
        AtmosChatbotService.save_message(conversation_id, "human" if i % 2 == 0 else "ai", f"Msg {i}")

    history = AtmosChatbotService.get_history(conversation_id)
    # It must be capped at MAX_HISTORY (10 messages)
    assert len(history) == 10
    assert history[0] == ("human", "Msg 2")
    assert history[-1] == ("ai", "Msg 11")

def test_chat_non_stream_endpoint(client):
    # Tests non-streaming route under mock mode
    response = client.post("/api/chat", json={"message": "Tell me about Rohini", "language": "en"})
    assert response.status_code == 200
    data = response.json()
    assert data["language"] == "en"
    assert "Rohini: current AQI" in data["response"]
    assert "245" not in data["response"]

def test_chat_stream_endpoint_mock_mode(client):
    # Tests streaming route (Accept: text/event-stream) under mock mode
    headers = {"Accept": "text/event-stream"}
    response = client.post("/api/chat", json={"message": "Tell me about Dwarka", "language": "en"}, headers=headers)
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    # Read events
    events = []
    for line in response.iter_lines():
        if isinstance(line, bytes):
            line = line.decode("utf-8")
        if line.startswith("data: "):
            data_str = line[6:]
            events.append(json.loads(data_str))

    assert len(events) > 1
    # Check that text segments are streamed and done is True at the end
    assert any(not e.get("done") and "Dwarka" in e.get("text", "") for e in events[:-1])
    assert events[-1]["done"] is True
    assert any("Atmos forecast snapshot" in src for src in events[-1]["sources"])


def test_context_includes_provenance():
    context = build_context_payload("How is Rohini?")
    assert "=== Data Provenance ===" in context
    assert "freshness: sample" in context
    assert "NOT current conditions" in context


def test_provider_failure_falls_back_to_snapshot_data(client, monkeypatch):
    """A failing Gemini call must answer from real data, never canned numbers."""
    from langchain_core.runnables import RunnableLambda
    import services.chatbot as chatbot

    def failing_llm(**kwargs):
        def fail(_):
            raise RuntimeError("quota exceeded")
        return RunnableLambda(fail)

    monkeypatch.setattr(chatbot, "ChatGoogleGenerativeAI", failing_llm)
    monkeypatch.setattr(AtmosChatbotService, "should_use_mock", classmethod(lambda cls, force_rag=False: False))

    data = client.post("/api/chat", json={"message": "What is Delhi's average AQI?", "language": "en"}).json()
    assert data["response"].startswith("The AI assistant is unavailable right now.")
    avg = round(client.get("/api/forecast/delhi").json()["city_avg_aqi"])
    assert f"Delhi's average AQI is {avg}" in data["response"]

    # Streaming takes the same fallback when the provider fails before any text
    events = []
    with client.stream("POST", "/api/chat", json={"message": "Tell me about Rohini", "language": "en"},
                       headers={"Accept": "text/event-stream"}) as resp:
        for line in resp.iter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
    text = "".join(e.get("text", "") for e in events)
    assert "Rohini: current AQI" in text
    assert events[-1]["done"] is True and "error" not in events[-1]


# ── Language reaches the real prompt (F20) ───────────────────────────────────

@pytest.fixture
def captured_prompts(monkeypatch):
    """Replace Gemini with a stub that records the assembled prompt."""
    from langchain_core.runnables import RunnableLambda
    from langchain_core.messages import AIMessage
    import services.chatbot as chatbot

    prompts = []

    def stub_llm(**kwargs):
        def respond(prompt_value):
            prompts.append(prompt_value.to_messages())
            return AIMessage(content="stub reply")
        return RunnableLambda(respond)

    monkeypatch.setattr(chatbot, "ChatGoogleGenerativeAI", stub_llm)
    monkeypatch.setattr(AtmosChatbotService, "should_use_mock", classmethod(lambda cls, force_rag=False: False))
    return prompts


def _system_text(messages):
    return next(m.content for m in messages if m.type == "system")


def test_hindi_selection_with_english_query_requests_hindi(client, captured_prompts):
    data = client.post("/api/chat", json={"message": "How is the air in Rohini?", "language": "hi"}).json()
    assert data["response"] == "stub reply"
    assert data["language"] == "hi"
    assert "Respond in Hindi (हिंदी)" in _system_text(captured_prompts[-1])

    # Same instruction on the streaming path
    with client.stream("POST", "/api/chat", json={"message": "How is the air in Rohini?", "language": "hi"},
                       headers={"Accept": "text/event-stream"}) as resp:
        list(resp.iter_lines())
    assert "Respond in Hindi (हिंदी)" in _system_text(captured_prompts[-1])


def test_english_and_unsupported_languages_request_english(client, captured_prompts):
    for lang in ("en", "fr", ""):
        data = client.post("/api/chat", json={"message": "AQI?", "language": lang}).json()
        assert data["language"] == "en"
        system = _system_text(captured_prompts[-1])
        assert "Respond in English" in system
        assert "{language_instruction}" not in system
