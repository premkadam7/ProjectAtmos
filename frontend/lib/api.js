import {
  USE_MOCK,
  mockForecast,
  mockWardDetail,
  mockBlame,
  mockEnforce,
  mockVulnerable,
  mockWhatIf,
} from './mockData';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Backend data refreshes every ~30 min, so reuse GET responses briefly: this
// dedupes concurrent requests and makes moving between pages instant.
const CACHE_TTL_MS = 60 * 1000;
const responseCache = new Map();

function cachedGet(path) {
  const hit = responseCache.get(path);
  if (hit && Date.now() - hit.at < CACHE_TTL_MS) return hit.promise;
  const promise = fetch(`${BASE_URL}${path}`).then((res) => res.json());
  responseCache.set(path, { at: Date.now(), promise });
  promise.catch(() => responseCache.delete(path));
  return promise;
}

export async function getForecast(city) {
  if (USE_MOCK) return mockForecast;
  return cachedGet(`/api/forecast/${city}`);
}

export async function getWardDetail(city, wardId) {
  if (USE_MOCK) return mockWardDetail;
  return cachedGet(`/api/forecast/${city}/${wardId}`);
}

export async function getBlame(city, wardId) {
  if (USE_MOCK) return mockBlame;
  return cachedGet(`/api/blame/${city}/${wardId}`);
}

export async function getTimeline(city) {
  return cachedGet(`/api/forecast/${city}/timeline`);
}

export async function getHistory(city, { wardId, hours = 720 } = {}) {
  const params = new URLSearchParams({ hours: String(hours) });
  if (wardId) params.set('ward_id', wardId);
  return cachedGet(`/api/history/${city}?${params}`);
}

export async function getEnforce(city) {
  if (USE_MOCK) return mockEnforce;
  const res = await fetch(`${BASE_URL}/api/enforce/${city}`);
  return res.json();
}

export async function getVulnerable(city) {
  if (USE_MOCK) return mockVulnerable;
  const res = await fetch(`${BASE_URL}/api/vulnerable/${city}`);
  return res.json();
}

export async function postWhatIf(wardId, intervention, durationHours) {
  if (USE_MOCK) return mockWhatIf;
  const res = await fetch(`${BASE_URL}/api/whatif`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ward_id: wardId, intervention, duration_hours: durationHours }),
  });
  return res.json();
}

export async function postChat(message, language = 'en', conversationId = null) {
  if (USE_MOCK) return {
    response: `This is a mock response for: "${message}". In production, this will be powered by the RAG chatbot with real Delhi AQI data.`,
    language,
    conversation_id: 'mock_conv_001',
    sources: ['Mock Data'],
  };
  const res = await fetch(`${BASE_URL}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, language, conversation_id: conversationId }),
  });
  return res.json();
}