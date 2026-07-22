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
    assert "Rohini" in data["response"]
    assert "245" in data["response"]

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
    assert "Forecast Data" in events[-1]["sources"]
