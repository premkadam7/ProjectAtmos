import sys
import os
from unittest.mock import MagicMock

# Adjust sys.path so backend modules can be imported
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Tests run offline against the bundled sample data, never the live APIs
os.environ.setdefault("ATMOS_LIVE", "0")

import pytest
from fastapi.testclient import TestClient

# Import the app
from main import app

# ── Tracked files must be byte-identical after the suite ──
def _tracked_file_hashes():
    import hashlib
    import subprocess
    try:
        files = subprocess.run(
            ["git", "ls-files", "-z", "--", "."], cwd=backend_dir, capture_output=True, check=True,
        ).stdout.decode().split("\0")
    except (OSError, subprocess.CalledProcessError):
        return None
    hashes = {}
    for rel in filter(None, files):
        path = os.path.join(backend_dir, rel)
        if os.path.isfile(path):
            with open(path, "rb") as f:
                hashes[rel] = hashlib.sha256(f.read()).hexdigest()
    return hashes


@pytest.fixture(scope="session", autouse=True)
def tracked_files_unchanged():
    before = _tracked_file_hashes()
    yield
    if before is None:
        return
    after = _tracked_file_hashes()
    changed = sorted(f for f in before if after.get(f) != before[f])
    assert not changed, f"Tests modified tracked files: {changed}"


# ── Pytest Fixture client ──
@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# ── Session-wide Mocks for Network/External Services ──
@pytest.fixture(scope="session", autouse=True)
def mock_external_services():
    # Mock httpx send to intercept any external HTTP calls
    import httpx
    original_send = httpx.Client.send
    
    def mock_send(self, request, *args, **kwargs):
        url = str(request.url)
        if "testserver" in url or "localhost" in url or "127.0.0.1" in url:
            return original_send(self, request, *args, **kwargs)
        resp = httpx.Response(
            status_code=200,
            json={"status": "mocked", "info": "external network request intercepted"},
            request=request
        )
        return resp
        
    httpx.Client.send = mock_send

    original_async_send = httpx.AsyncClient.send
    async def mock_async_send(self, request, *args, **kwargs):
        url = str(request.url)
        if "testserver" in url or "localhost" in url or "127.0.0.1" in url:
            return await original_async_send(self, request, *args, **kwargs)
        resp = httpx.Response(
            status_code=200,
            json={"status": "mocked", "info": "external network request intercepted"},
            request=request
        )
        return resp
        
    httpx.AsyncClient.send = mock_async_send

    # Mock requests send to intercept any external HTTP calls
    import requests
    original_requests_send = requests.Session.send
    
    def mock_requests_send(self, request, *args, **kwargs):
        resp = requests.Response()
        resp.status_code = 200
        resp._content = b'{"status": "mocked", "info": "external network request intercepted"}'
        resp.url = request.url
        resp.request = request
        return resp
        
    requests.Session.send = mock_requests_send

    # Mock langchain/google generative ai components if used
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        ChatGoogleGenerativeAI.invoke = MagicMock(return_value=MagicMock(content="Mocked response from Gemini"))
        ChatGoogleGenerativeAI._generate = MagicMock(return_value=MagicMock())
    except ImportError:
        pass

    try:
        import google.generativeai as genai
        genai.GenerativeModel = MagicMock()
        genai.configure = MagicMock()
    except ImportError:
        pass
