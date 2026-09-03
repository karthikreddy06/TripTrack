import { useState, useEffect, useRef } from 'react';
import {
  Sparkles,
  X,
  Send,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  ChevronRight,
  MapPin,
  RefreshCw
} from 'lucide-react';
import { aiAPI, tripsAPI, extractErrorMessage } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { SafeImage } from './SafeImage';

let msgCounter = 0;
const getNextMsgId = (prefix) => `${prefix}_${++msgCounter}`;

export const AIAssistantDrawer = () => {
  const { isAuthenticated } = useAuth();
  const { showError, showSuccess } = useToast();

  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState('conv_agent_session');
  const [trips, setTrips] = useState([]);
  const [activeTripId, setActiveTripId] = useState('');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Sync conversationId with localStorage
  useEffect(() => {
    localStorage.setItem('traveltrack_chat_cid', conversationId);
  }, [conversationId]);

  // Load user trips for context selector
  useEffect(() => {
    if (!isAuthenticated) return;
    const fetchTrips = async () => {
      try {
        const res = await tripsAPI.getTrips();
        const userTrips = res.trips || [];
        setTrips(userTrips);
        if (userTrips.length > 0) {
          setActiveTripId((prev) => prev || userTrips[0]._id || userTrips[0].trip_id);
        }
      } catch {
        // Non-fatal
      }
    };
    fetchTrips();
  }, [isAuthenticated, isOpen]);

  // Auto-scroll to bottom of messages
  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isOpen]);

  // Focus input on open
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 150);
    }
  }, [isOpen]);

  if (!isAuthenticated) return null;

  const handleSendMessage = async (textToSend = null, confirmActionVal = null) => {
    const text = (textToSend !== null ? textToSend : inputValue).trim();
    if (!text && confirmActionVal === null) return;

    const userMsg = {
      id: getNextMsgId('u'),
      role: 'user',
      content: text || (confirmActionVal ? 'Confirm Action' : 'Cancel Action'),
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (textToSend === null) setInputValue('');
    setLoading(true);

    try {
      const res = await aiAPI.sendMessage({
        message: text || (confirmActionVal ? 'confirm' : 'cancel'),
        tripId: activeTripId || undefined,
        conversationId,
        confirmAction: confirmActionVal !== null ? confirmActionVal : undefined,
      });

      const aiMsg = {
        id: getNextMsgId('a'),
        role: 'assistant',
        content: res.response,
        timestamp: new Date().toISOString(),
        tool_called: res.tool_called,
        tool_result: res.tool_result,
        pending_action: res.pending_action,
        action_status: res.action_status,
        places: res.places,
      };

      setMessages((prev) => [...prev, aiMsg]);

      // If a database modification occurred, notify open views to re-fetch!
      if (res.mutation_occurred) {
        window.dispatchEvent(
          new CustomEvent('traveltrack-data-updated', {
            detail: {
              entity: res.affected_entity,
              tripId: activeTripId,
            },
          })
        );
        showSuccess('TravelTrack updated successfully.');
      }
    } catch (err) {
      const errDetail = extractErrorMessage(err);
      setMessages((prev) => [
        ...prev,
        {
          id: `err_${Date.now()}`,
          role: 'assistant',
          content: `❌ I encountered an error executing that request: ${errDetail}`,
          timestamp: new Date().toISOString(),
          action_status: 'failed',
        },
      ]);
      showError(errDetail);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleClearChat = async () => {
    try {
      await aiAPI.clearChatHistory(conversationId);
      setMessages([]);
      const newCid = `conv_${Date.now().toString(36)}`;
      setConversationId(newCid);
      showSuccess('Conversation history cleared.');
    } catch {
      setMessages([]);
    }
  };

  const QUICK_PROMPTS = [
    { label: '💰 Check my budget', text: 'How much budget do I have left?' },
    { label: '📍 Find places in Hyderabad', text: 'Find top attractions in Hyderabad' },
    { label: '📅 What am I doing Day 1?', text: 'What am I doing on Day 1?' },
    { label: '🧾 Add ₹500 for dinner', text: 'Add an expense of ₹500 for dinner' },
  ];

  return (
    <>
      {/* Floating Trigger Button */}
      <button
        type="button"
        className="ai-drawer-trigger-btn"
        onClick={() => setIsOpen(true)}
        title="Open TravelTrack AI Agent"
        style={{
          position: 'fixed',
          bottom: '1.5rem',
          right: '1.5rem',
          zIndex: 990,
          display: isOpen ? 'none' : 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          padding: '0.75rem 1.15rem',
          borderRadius: '999px',
          backgroundColor: 'var(--primary-dark, #1B3022)',
          color: 'var(--primary-cream, #F4EFE6)',
          border: '1px solid var(--border-soft, #D8CFBE)',
          boxShadow: '0 8px 24px rgba(27, 48, 34, 0.22)',
          cursor: 'pointer',
          fontWeight: 600,
          fontSize: '0.9rem',
          transition: 'all 0.25s ease',
        }}
      >
        <Sparkles size={16} style={{ color: 'var(--accent-sage, #8EB897)' }} />
        <span>Ask AI Agent</span>
      </button>

      {/* Slide-over Backdrop */}
      {isOpen && (
        <div
          className="ai-drawer-backdrop"
          onClick={() => setIsOpen(false)}
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(27, 48, 34, 0.35)',
            backdropFilter: 'blur(3px)',
            zIndex: 998,
            transition: 'opacity 0.25s ease',
          }}
        />
      )}

      {/* Slide-over Drawer Panel */}
      <div
        className={`ai-drawer-panel ${isOpen ? 'open' : ''}`}
        style={{
          position: 'fixed',
          top: 0,
          right: 0,
          bottom: 0,
          width: '100%',
          maxWidth: '460px',
          backgroundColor: 'var(--bg-main, #FAF7F2)',
          borderLeft: '1px solid var(--border-soft, #D8CFBE)',
          boxShadow: '-8px 0 32px rgba(27, 48, 34, 0.16)',
          zIndex: 999,
          display: 'flex',
          flexDirection: 'column',
          transform: isOpen ? 'translateX(0)' : 'translateX(100%)',
          transition: 'transform 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
        }}
      >
        {/* Drawer Header */}
        <div
          style={{
            padding: '1rem 1.25rem',
            borderBottom: '1px solid var(--border-soft, #D8CFBE)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            backgroundColor: 'var(--bg-card, #FFFFFF)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                backgroundColor: 'rgba(95, 155, 104, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--primary-green, #5F9B68)',
              }}
            >
              <Sparkles size={16} />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '0.95rem', color: 'var(--text-primary)' }}>
                TravelTrack AI Agent
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Live Actions & Grounded Reasoning
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={handleClearChat}
              title="Clear current conversation"
              style={{ padding: '0.35rem 0.6rem' }}
            >
              <Trash2 size={13} />
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => setIsOpen(false)}
              style={{ padding: '0.35rem 0.6rem' }}
            >
              <X size={15} />
            </button>
          </div>
        </div>

        {/* Active Trip Context Selector */}
        {trips.length > 0 && (
          <div
            style={{
              padding: '0.5rem 1.25rem',
              backgroundColor: 'rgba(216, 207, 190, 0.18)',
              borderBottom: '1px solid var(--border-soft, #D8CFBE)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              fontSize: '0.8rem',
            }}
          >
            <span style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>Active Trip:</span>
            <select
              value={activeTripId}
              onChange={(e) => setActiveTripId(e.target.value)}
              style={{
                padding: '0.2rem 0.5rem',
                borderRadius: '6px',
                border: '1px solid var(--border-soft)',
                backgroundColor: 'var(--bg-card)',
                fontSize: '0.8rem',
                color: 'var(--text-primary)',
                maxWidth: '260px',
              }}
            >
              <option value="">All Trips / General</option>
              {trips.map((t) => (
                <option key={t._id || t.trip_id} value={t._id || t.trip_id}>
                  {t.title} ({t.destination})
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Messages Scroll Area */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '1.25rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '1rem',
          }}
        >
          {messages.length === 0 ? (
            <div
              style={{
                textAlign: 'center',
                margin: 'auto 0',
                padding: '1rem',
                color: 'var(--text-secondary)',
              }}
            >
              <div
                style={{
                  width: '48px',
                  height: '48px',
                  borderRadius: '50%',
                  backgroundColor: 'rgba(95, 155, 104, 0.12)',
                  color: 'var(--primary-green)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 0.75rem',
                }}
              >
                <Sparkles size={22} />
              </div>
              <h4 style={{ fontWeight: 700, marginBottom: '0.4rem', color: 'var(--text-primary)' }}>
                How can I assist your travels?
              </h4>
              <p style={{ fontSize: '0.85rem', marginBottom: '1.25rem', lineHeight: 1.5 }}>
                I have direct access to your trips, itineraries, budgets, and OpenStreetMap Explore places.
              </p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                {QUICK_PROMPTS.map((qp, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => handleSendMessage(qp.text)}
                    style={{
                      padding: '0.55rem 0.85rem',
                      borderRadius: '8px',
                      border: '1px solid var(--border-soft)',
                      backgroundColor: 'var(--bg-card)',
                      color: 'var(--text-primary)',
                      fontSize: '0.8rem',
                      textAlign: 'left',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                    }}
                  >
                    <span>{qp.label}</span>
                    <ChevronRight size={13} style={{ color: 'var(--text-muted)' }} />
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((m) => (
              <div
                key={m.id}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: m.role === 'user' ? 'flex-end' : 'flex-start',
                  width: '100%',
                }}
              >
                {/* Message Bubble */}
                <div
                  style={{
                    maxWidth: '88%',
                    padding: '0.85rem 1rem',
                    borderRadius:
                      m.role === 'user' ? '14px 14px 2px 14px' : '14px 14px 14px 2px',
                    backgroundColor:
                      m.role === 'user' ? 'var(--primary-green, #5F9B68)' : 'var(--bg-card, #FFFFFF)',
                    color: m.role === 'user' ? '#FFFFFF' : 'var(--text-primary, #2A2A2A)',
                    border:
                      m.role === 'user'
                        ? 'none'
                        : '1px solid var(--border-soft, #D8CFBE)',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
                    fontSize: '0.88rem',
                    lineHeight: 1.55,
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                  }}
                >
                  {/* Tool execution badge */}
                  {m.tool_called && (
                    <div
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.35rem',
                        fontSize: '0.72rem',
                        padding: '0.15rem 0.45rem',
                        borderRadius: '4px',
                        backgroundColor: 'rgba(95, 155, 104, 0.15)',
                        color: 'var(--primary-green)',
                        fontWeight: 600,
                        marginBottom: '0.5rem',
                      }}
                    >
                      <CheckCircle2 size={11} />
                      <span>{m.tool_called}</span>
                    </div>
                  )}

                  {m.content}

                  {/* Place cards if returned */}
                  {m.places && m.places.length > 0 && (
                    <div style={{ marginTop: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      {m.places.slice(0, 3).map((p, pIdx) => (
                        <div
                          key={p.id || pIdx}
                          style={{
                            display: 'flex',
                            gap: '0.6rem',
                            padding: '0.5rem',
                            borderRadius: '8px',
                            backgroundColor: 'rgba(0,0,0,0.03)',
                            border: '1px solid var(--border-soft)',
                          }}
                        >
                          {p.image_url ? (
                            <div style={{ width: '48px', height: '48px', borderRadius: '6px', overflow: 'hidden', flexShrink: 0 }}>
                              <SafeImage src={p.image_url} alt={p.name} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                            </div>
                          ) : (
                            <div style={{ width: '48px', height: '48px', borderRadius: '6px', backgroundColor: 'rgba(95,155,104,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--primary-green)', flexShrink: 0 }}>
                              <MapPin size={18} />
                            </div>
                          )}
                          <div style={{ overflow: 'hidden' }}>
                            <div style={{ fontWeight: 600, fontSize: '0.8rem', color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                              {p.name}
                            </div>
                            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                              {p.category || 'Sight'} • {p.address || p.location || ''}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Confirmation Prompt Card */}
                  {m.pending_action && (
                    <div
                      style={{
                        marginTop: '0.85rem',
                        padding: '0.75rem',
                        borderRadius: '8px',
                        backgroundColor: 'rgba(239, 68, 68, 0.08)',
                        border: '1px solid rgba(239, 68, 68, 0.25)',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#B91C1C', fontWeight: 600, fontSize: '0.82rem', marginBottom: '0.5rem' }}>
                        <AlertTriangle size={14} />
                        <span>Action Confirmation Required</span>
                      </div>
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button
                          type="button"
                          className="btn btn-primary btn-sm"
                          style={{ backgroundColor: '#B91C1C', borderColor: '#B91C1C', padding: '0.35rem 0.75rem', fontSize: '0.78rem' }}
                          onClick={() => handleSendMessage(null, true)}
                          disabled={loading}
                        >
                          Confirm & Delete
                        </button>
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          style={{ padding: '0.35rem 0.75rem', fontSize: '0.78rem' }}
                          onClick={() => handleSendMessage(null, false)}
                          disabled={loading}
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}

          {/* Loading Indicator */}
          {loading && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.75rem 1rem',
                borderRadius: '14px 14px 14px 2px',
                backgroundColor: 'var(--bg-card)',
                border: '1px solid var(--border-soft)',
                color: 'var(--text-secondary)',
                fontSize: '0.82rem',
                width: 'fit-content',
              }}
            >
              <RefreshCw size={13} className="spinner" />
              <span>AI is consulting TravelTrack data...</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div
          style={{
            padding: '0.85rem 1.25rem',
            borderTop: '1px solid var(--border-soft, #D8CFBE)',
            backgroundColor: 'var(--bg-card, #FFFFFF)',
            display: 'flex',
            gap: '0.5rem',
            alignItems: 'center',
          }}
        >
          <input
            ref={inputRef}
            type="text"
            className="input-field"
            placeholder="Ask AI or type an action (e.g. 'Add Charminar to Day 2')..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
            style={{
              flex: 1,
              padding: '0.65rem 0.9rem',
              fontSize: '0.86rem',
              borderRadius: '8px',
              border: '1px solid var(--border-soft)',
            }}
          />
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => handleSendMessage()}
            disabled={loading || !inputValue.trim()}
            style={{
              padding: '0.65rem 0.9rem',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Send size={15} />
          </button>
        </div>
      </div>
    </>
  );
};
