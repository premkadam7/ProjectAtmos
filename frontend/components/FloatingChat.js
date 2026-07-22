'use client';

import { useState, useRef, useEffect } from 'react';
import { postChat } from '@/lib/api';

const SUGGESTIONS = [
  "How's the air in Dwarka?",
  "Worst areas today?",
  "Safe to jog outside?",
  "What's causing the pollution spike?",
];

const LANGUAGES = [
  { code: 'en', label: 'EN' },
  { code: 'hi', label: 'HI' },
];

export default function FloatingChat() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      role: 'bot',
      text: "Hi! I'm Atmos Assistant 🌿 Ask me about Delhi's air quality, forecasts, or safe zones.",
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [language, setLanguage] = useState('en');
  const [convId, setConvId] = useState(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    if (open) bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, open]);

  async function send(text) {
    const msg = text || input.trim();
    if (!msg || loading) return;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', text: msg }]);
    setLoading(true);
    try {
      const res = await postChat(msg, language, convId);
      setConvId(res.conversation_id);
      setMessages(prev => [...prev, { role: 'bot', text: res.response }]);
    } catch {
      setMessages(prev => [...prev, { role: 'bot', text: 'Sorry, something went wrong. Try again.' }]);
    } finally {
      setLoading(false);
    }
  }

  function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  return (
    <>
      {/* Chat Panel */}
      {open && (
        <div className="chat-panel">

          {/* Header */}
          <div className="chat-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{
                width: '28px', height: '28px', borderRadius: '8px',
                background: 'var(--accent-gradient)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '14px',
              }}>
                🌿
              </div>
              <div>
                <p style={{ fontSize: '13px', fontWeight: '700', background: 'var(--accent-gradient)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                  Atmos Assistant
                </p>
                <p style={{ fontSize: '10px', color: 'var(--text-dim)' }}>AI-powered air quality advisor</p>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              {/* Language toggle */}
              <div style={{ display: 'flex', background: 'var(--bg-tertiary)', borderRadius: '20px', padding: '2px' }}>
                {LANGUAGES.map(l => (
                  <button
                    key={l.code}
                    onClick={() => setLanguage(l.code)}
                    style={{
                      padding: '3px 10px',
                      borderRadius: '20px',
                      border: 'none',
                      background: language === l.code ? 'var(--accent-gradient)' : 'transparent',
                      color: language === l.code ? 'white' : 'var(--text-dim)',
                      fontSize: '11px',
                      fontWeight: '600',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease',
                    }}
                  >
                    {l.label}
                  </button>
                ))}
              </div>
              <button
                onClick={() => setOpen(false)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '16px', lineHeight: 1 }}
              >
                ✕
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="chat-messages">
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`chat-bubble ${msg.role}`}
                style={{ alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start' }}
              >
                {msg.text}
              </div>
            ))}
            {loading && (
              <div className="chat-bubble bot" style={{ alignSelf: 'flex-start' }}>
                <div className="typing-dots">
                  <span /><span /><span />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Suggestion chips */}
          {messages.length <= 1 && (
            <div className="suggestion-chips">
              {SUGGESTIONS.map(s => (
                <button key={s} className="suggestion-chip" onClick={() => send(s)}>
                  {s}
                </button>
              ))}
            </div>
          )}

          {/* Input */}
          <div className="chat-input-area">
            <input
              className="chat-input"
              placeholder={language === 'hi' ? 'वायु गुणवत्ता के बारे में पूछें...' : 'Ask about air quality...'}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              disabled={loading}
            />
            <button className="chat-send" onClick={() => send()} disabled={loading || !input.trim()}>
              ➤
            </button>
          </div>

        </div>
      )}

      {/* FAB */}
      <button
        className="chat-fab"
        onClick={() => setOpen(v => !v)}
        aria-label="Toggle chat"
        style={{ fontSize: open ? '20px' : '22px' }}
      >
        {open ? '✕' : '💬'}
      </button>
    </>
  );
}