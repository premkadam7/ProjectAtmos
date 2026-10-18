import {
  USE_MOCK,
  mockForecast,
  mockWardDetail,
  mockBlame,
  mockEnforce,
  mockVulnerable,
  mockWhatIf,
} from './mockData';

export const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export class ApiError extends Error {
  constructor(message, { status = null, path = '' } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.path = path;
  }
}

/**
 * fetch with a timeout that throws ApiError for network failures, timeouts,
 * non-2xx responses (using the backend's `detail` message) and non-JSON bodies.
 */
async function request(path, { method = 'GET', body, timeoutMs = 30000 } = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  let res;
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      method,
      signal: controller.signal,
      ...(body !== undefined && { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
    });
  } catch (err) {
    throw new ApiError(
      err.name === 'AbortError'
        ? `No response within ${timeoutMs / 1000}s`
        : 'No response (the server is not running, the URL is wrong, or CORS blocked this site)',
      { path },
    );
  } finally {
    clearTimeout(timer);
  }
  let data = null;
  try {
    data = await res.json();
  } catch {
    if (res.ok) throw new ApiError(`API returned an unreadable response for ${path}`, { status: res.status, path });
  }
  if (!res.ok) {
    const detail = typeof data?.detail === 'string' ? data.detail : `API responded ${res.status}`;
    throw new ApiError(detail, { status: res.status, path });
  }
  return data;
}

// Backend data refreshes every ~30 min, so reuse GET responses briefly: this
// dedupes concurrent requests and makes moving between pages instant.
const CACHE_TTL_MS = 60 * 1000;
const responseCache = new Map();

function cachedGet(path) {
  const hit = responseCache.get(path);
  if (hit && Date.now() - hit.at < CACHE_TTL_MS) return hit.promise;
  const promise = request(path);
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
  return cachedGet(`/api/enforce/${city}`);
}

export async function getVulnerable(city) {
  if (USE_MOCK) return mockVulnerable;
  return cachedGet(`/api/vulnerable/${city}`);
}

export async function postWhatIf(wardId, intervention, durationHours) {
  if (USE_MOCK) return mockWhatIf;
  return request('/api/whatif', {
    method: 'POST',
    body: { ward_id: wardId, intervention, duration_hours: durationHours },
  });
}

export async function postChat(message, language = 'en', conversationId = null) {
  if (USE_MOCK) return {
    response: `This is a mock response for: "${message}". In production, this will be powered by the RAG chatbot with real Delhi AQI data.`,
    language,
    conversation_id: 'mock_conv_001',
    sources: ['Mock Data'],
  };
  return request('/api/chat', {
    method: 'POST',
    body: { message, language, conversation_id: conversationId },
    timeoutMs: 60000,
  });
}