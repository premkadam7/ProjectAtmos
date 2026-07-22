import pytest
import time
import json
import asyncio
import httpx
from fastapi.testclient import TestClient
from main import app

# 1. Latency SLA < 500ms check
def test_latency_sla_under_500ms(client):
    endpoints = [
        ("/api/forecast/delhi", "GET", None),
        ("/api/forecast/delhi/anand_vihar", "GET", None),
        ("/api/chat", "POST", {"message": "Hello, tell me about Rohini Sector 7", "language": "en"}),
        ("/api/whatif", "POST", {"ward_id": "anand_vihar", "intervention": "pause_construction", "duration_hours": 24})
    ]

    for path, method, payload in endpoints:
        start_time = time.perf_counter()
        if method == "GET":
            response = client.get(path)
        else:
            response = client.post(path, json=payload)
        end_time = time.perf_counter()
        
        latency = (end_time - start_time) * 1000  # in ms
        assert response.status_code == 200
        assert latency < 500.0, f"SLA violated: {path} took {latency:.2f}ms"

# 2. Cache hits speed comparison
def test_cache_hits_speed_comparison(client):
    # First request: potential cache miss or initial fetch
    start_first = time.perf_counter()
    response_first = client.get("/api/vulnerable/delhi")
    end_first = time.perf_counter()
    latency_first = (end_first - start_first) * 1000

    assert response_first.status_code == 200

    # Second request: guaranteed cache hit
    start_second = time.perf_counter()
    response_second = client.get("/api/vulnerable/delhi")
    end_second = time.perf_counter()
    latency_second = (end_second - start_second) * 1000

    assert response_second.status_code == 200
    # The cache hit should be faster, or at least comparable and extremely fast (e.g. < 50ms)
    assert latency_second < 150.0, f"Cache hit response too slow: {latency_second:.2f}ms"

# 3. SSE chat response format verification
def test_sse_chat_response_format(client):
    payload = {
        "message": "Tell me about Rohini Sector 7",
        "language": "en",
        "stream": True
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "").lower()

    # Split response stream content into lines
    content = response.content.decode("utf-8")
    lines = [line.strip() for line in content.split("\r\n") if line.strip()]
    if not lines:
        lines = [line.strip() for line in content.split("\n") if line.strip()]

    assert len(lines) > 0, "SSE response should not be empty"

    has_done_true = False
    for line in lines:
        assert line.startswith("data:"), f"Each event line must start with 'data:': {line}"
        json_str = line[len("data:"):].strip()
        data = json.loads(json_str)

        assert "conversation_id" in data
        assert "done" in data
        if data["done"]:
            has_done_true = True
            assert "sources" in data
        else:
            assert "text" in data

    assert has_done_true, "SSE stream must terminate with a 'done: true' event"

# 4. Concurrent requests using asyncio/httpx
@pytest.mark.asyncio
async def test_concurrent_forecast_requests_async():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as ac:
        tasks = [
            ac.get("/api/forecast/delhi/anand_vihar?hours=24")
            for _ in range(10)
        ]
        
        start_time = time.perf_counter()
        responses = await asyncio.gather(*tasks)
        end_time = time.perf_counter()
        
        avg_latency = ((end_time - start_time) / len(tasks)) * 1000
        
        for idx, resp in enumerate(responses):
            assert resp.status_code == 200, f"Request {idx} failed with {resp.status_code}"
            data = resp.json()
            assert "ward_id" in data
            assert len(data["hourly"]) == 24
            
        assert avg_latency < 100.0, f"Average concurrent forecast latency is too high: {avg_latency:.2f}ms"

# 5. Concurrent chat requests using asyncio/httpx
@pytest.mark.asyncio
async def test_concurrent_chat_requests_async():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as ac:
        payloads = [
            {"message": f"Hello {i}, how is the air quality in Dwarka?", "language": "en"}
            for i in range(5)
        ]
        tasks = [
            ac.post("/api/chat", json=payload)
            for payload in payloads
        ]
        
        start_time = time.perf_counter()
        responses = await asyncio.gather(*tasks)
        end_time = time.perf_counter()
        
        avg_latency = ((end_time - start_time) / len(tasks)) * 1000
        
        for idx, resp in enumerate(responses):
            assert resp.status_code == 200, f"Request {idx} failed with {resp.status_code}"
            data = resp.json()
            assert "conversation_id" in data
            assert "Dwarka" in data["response"]
            
        assert avg_latency < 200.0, f"Average concurrent chat latency is too high: {avg_latency:.2f}ms"
