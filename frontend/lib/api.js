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

export async function getForecast(city) {
  if (USE_MOCK) return mockForecast;
  const res = await fetch(`${BASE_URL}/api/forecast/${city}`);
  return res.json();
}

export async function getWardDetail(city, wardId) {
  if (USE_MOCK) return mockWardDetail;
  const res = await fetch(`${BASE_URL}/api/forecast/${city}/${wardId}`);
  return res.json();
}

export async function getBlame(city, wardId) {
  if (USE_MOCK) return mockBlame;
  const res = await fetch(`${BASE_URL}/api/blame/${city}/${wardId}`);
  return res.json();
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