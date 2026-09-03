import { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import {
  Sparkles,
  MapPin,
  Compass,
  CheckCircle2,
  Clock,
  Briefcase,
  Lightbulb,
  ArrowLeft,
  BookmarkPlus,
  Navigation,
  X,
  Send,
  Trash2,
  AlertTriangle,
  RefreshCw,
  Layers
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { aiAPI, tripsAPI, itineraryAPI, extractErrorMessage } from '../services/api';
import { Alert } from '../components/Alert';
import { SafeImage } from '../components/SafeImage';
import { formatDistance } from '../utils/geo';

const INTEREST_OPTIONS = [
  'Culture & Heritage',
  'Local Cuisine & Food',
  'Nature & Landscapes',
  'Adventure & Hiking',
  'Beaches & Coastal',
  'Art & Museums',
  'Shopping & Markets',
  'Relaxation & Wellness',
  'Photography',
  'Nightlife & Music'
];

const STYLE_OPTIONS = [
  'Balanced',
  'Backpacker / Budget',
  'Luxury & Comfort',
  'Relaxed & Slow Travel',
  'Fast-paced / Highlights',
  'Family Friendly'
];

let plannerMsgCounter = 0;
const getPlannerMsgId = (prefix) => `${prefix}_${++plannerMsgCounter}`;

export const AIPlanner = () => {
  const { user } = useAuth();
  const { showSuccess, showError } = useToast();
  const navigate = useNavigate();
  const location = useLocation();

  const prefill = location.state?.prefill || {};

  const [formData, setFormData] = useState({
    destination: prefill.destination || '',
    days: 3,
    start_date: new Date().toISOString().split('T')[0],
    travelers: prefill.travelers || 1,
    budget: prefill.budget !== undefined ? String(prefill.budget) : '',
    interests: ['Culture & Heritage', 'Local Cuisine & Food'],
    travel_style: 'Balanced',
    anchor_place_id: prefill.anchor_place_id || null,
    anchor_place_name: prefill.anchor_place_name || null,
    include_wishlist: true,
  });

  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState(null);
  const [generatedPlan, setGeneratedPlan] = useState(null);
  const [savingTrip, setSavingTrip] = useState(false);
  const [activeDayIndex, setActiveDayIndex] = useState(0);

  // Tab & Agent Chat States
  const [activeTab, setActiveTab] = useState('agent'); // 'agent' | 'generator'
  const [chatMessages, setMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [conversationId, setConversationId] = useState(() => {
    return localStorage.getItem('traveltrack_chat_cid') || `conv_${Date.now().toString(36)}`;
  });
  const [userTrips, setUserTrips] = useState([]);
  const [selectedTripId, setSelectedTripId] = useState('');
  const chatEndRef = useRef(null);

  useEffect(() => {
    localStorage.setItem('traveltrack_chat_cid', conversationId);
  }, [conversationId]);

  useEffect(() => {
    const fetchUserTrips = async () => {
      try {
        const res = await tripsAPI.getTrips();
        const trips = res.trips || [];
        setUserTrips(trips);
        if (trips.length > 0 && !selectedTripId) {
          setSelectedTripId(trips[0]._id || trips[0].trip_id);
        }
      } catch {
        // Non-fatal
      }
    };
    fetchUserTrips();
  }, [selectedTripId]);

  useEffect(() => {
    if (activeTab === 'agent') {
      chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatMessages, activeTab]);

  const handleSendChatMessage = async (textToSend = null, confirmActionVal = null) => {
    const text = (textToSend !== null ? textToSend : chatInput).trim();
    if (!text && confirmActionVal === null) return;

    const userMsg = {
      id: getPlannerMsgId('u'),
      role: 'user',
      content: text || (confirmActionVal ? 'Confirm Action' : 'Cancel Action'),
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (textToSend === null) setChatInput('');
    setChatLoading(true);

    try {
      const res = await aiAPI.sendMessage({
        message: text || (confirmActionVal ? 'confirm' : 'cancel'),
        tripId: selectedTripId || undefined,
        conversationId,
        confirmAction: confirmActionVal !== null ? confirmActionVal : undefined,
      });

      const aiMsg = {
        id: getPlannerMsgId('a'),
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

      if (res.mutation_occurred) {
        window.dispatchEvent(
          new CustomEvent('traveltrack-data-updated', {
            detail: {
              entity: res.affected_entity,
              tripId: selectedTripId,
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
          content: `❌ I encountered an error: ${errDetail}`,
          timestamp: new Date().toISOString(),
          action_status: 'failed',
        },
      ]);
      showError(errDetail);
    } finally {
      setChatLoading(false);
    }
  };

  const handleClearChatSession = async () => {
    try {
      await aiAPI.clearChatHistory(conversationId);
      setMessages([]);
      const newCid = `conv_${Date.now().toString(36)}`;
      setConversationId(newCid);
      showSuccess('Conversation cleared.');
    } catch {
      setMessages([]);
    }
  };

  const toggleInterest = (interest) => {
    setFormData((prev) => {
      const exists = prev.interests.includes(interest);
      if (exists) {
        return { ...prev, interests: prev.interests.filter((i) => i !== interest) };
      }
      return { ...prev, interests: [...prev.interests, interest] };
    });
  };

  const handleClearAnchor = () => {
    setFormData((prev) => ({
      ...prev,
      anchor_place_id: null,
      anchor_place_name: null,
    }));
  };

  const handleGenerate = async (e) => {
    e.preventDefault();
    if (!formData.destination.trim()) {
      setError('Please enter a destination.');
      return;
    }

    try {
      setGenerating(true);
      setError(null);
      setGeneratedPlan(null);

      const plan = await aiAPI.planTrip({
        destination: formData.destination.trim(),
        days: parseInt(formData.days, 10) || 3,
        start_date: formData.start_date || undefined,
        travelers: parseInt(formData.travelers, 10) || 1,
        budget: formData.budget ? parseFloat(formData.budget) : undefined,
        interests: formData.interests,
        travel_style: formData.travel_style,
        anchor_place_id: formData.anchor_place_id || undefined,
        anchor_place_name: formData.anchor_place_name || undefined,
        include_wishlist: formData.include_wishlist,
      });

      setGeneratedPlan(plan);
      setActiveDayIndex(0);
      showSuccess('Grounded itinerary curated with real OpenStreetMap data!');
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setGenerating(false);
    }
  };

  // Convert AI generated plan into a real MongoDB Trip and activities
  const handleSaveAsTrip = async () => {
    if (!generatedPlan || !user?.user_id) return;

    try {
      setSavingTrip(true);

      const daysCount = generatedPlan.days || 3;
      const startDate = formData.start_date || new Date().toISOString().split('T')[0];
      const startD = new Date(startDate);
      const endD = new Date(startD);
      endD.setDate(startD.getDate() + (daysCount - 1));
      const endDate = endD.toISOString().split('T')[0];

      // 1. Create Trip
      const createdTrip = await tripsAPI.createTrip({
        user_id: user.user_id,
        destination: generatedPlan.destination,
        title: `${generatedPlan.destination} — ${formData.travel_style} Journey`,
        start_date: startDate,
        end_date: endDate,
        status: 'planned',
        budget: parseFloat(formData.budget) || (daysCount * 140),
        travelers: parseInt(formData.travelers, 10) || 1,
        description: generatedPlan.summary,
        notes: `Itinerary Strategy:\n${generatedPlan.itinerary_rationale || ''}\n\nPacking:\n- ${generatedPlan.packing_list?.slice(0, 5).join('\n- ')}`,
      });

      const tripId = createdTrip.trip_id;

      // 2. Insert Activities into Itinerary
      if (generatedPlan.itinerary && Array.isArray(generatedPlan.itinerary)) {
        for (const day of generatedPlan.itinerary) {
          const actDate = day.date || startDate;
          if (day.activities && Array.isArray(day.activities)) {
            for (const act of day.activities) {
              await itineraryAPI.createActivity({
                trip_id: tripId,
                day_number: day.day,
                date: actDate,
                time: act.time || '09:30 AM',
                title: act.title,
                location: act.location || '',
                description: act.description || '',
                cost: parseFloat(act.estimated_cost) || 0,
                notes: act.category ? `Category: ${act.category}` : undefined,
              });
            }
          }
        }
      }

      showSuccess(`Trip to ${generatedPlan.destination} and all activities saved!`);
      navigate(`/trips/${tripId}`);
    } catch (err) {
      showError(extractErrorMessage(err));
    } finally {
      setSavingTrip(false);
    }
  };

  const formatCurrency = (val) =>
    new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(val || 0);

  return (
    <div className="main-content">
      <Link
        to="/dashboard"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.45rem',
          marginBottom: '1.5rem',
          color: 'var(--text-secondary)',
          fontWeight: 500,
          fontSize: '0.8rem',
          fontFamily: 'var(--font-mono)',
          textTransform: 'uppercase',
          letterSpacing: '0.04em',
        }}
      >
        <ArrowLeft size={14} />
        <span>Back to dashboard</span>
      </Link>

      <div className="dashboard-header">
        <div className="dashboard-title-group">
          <div className="editorial-mark">
            <i></i> 05 / GROUNDED AI TRAVEL PLANNER & AGENT
          </div>
          <h1>
            Intelligent journeys, <br />
            <em>grounded in real places.</em>
          </h1>
          <p className="welcome-subtitle">
            Interact with your real context-aware AI travel agent to manage trips, itineraries, budgets, and explore places worldwide.
          </p>
        </div>
      </div>

      {/* Mode Tabs */}
      <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.75rem', flexWrap: 'wrap' }}>
        <button
          type="button"
          onClick={() => setActiveTab('agent')}
          className={`btn ${activeTab === 'agent' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', padding: '0.65rem 1.25rem', borderRadius: '10px' }}
        >
          <Sparkles size={16} />
          <span>AI Travel Agent (Chat & Actions)</span>
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('generator')}
          className={`btn ${activeTab === 'generator' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', padding: '0.65rem 1.25rem', borderRadius: '10px' }}
        >
          <Layers size={16} />
          <span>Structured Itinerary Generator</span>
        </button>
      </div>

      {activeTab === 'agent' ? (
        <div
          className="card"
          style={{
            padding: 0,
            overflow: 'hidden',
            minHeight: '680px',
            display: 'flex',
            flexDirection: 'column',
            border: '1px solid var(--border-soft)',
            borderRadius: 'var(--radius-lg, 16px)',
            backgroundColor: 'var(--bg-card, #FFFFFF)'
          }}
        >
          {/* Agent Console Header */}
          <div
            style={{
              padding: '1.15rem 1.5rem',
              borderBottom: '1px solid var(--border-soft)',
              backgroundColor: 'var(--bg-main, #FAF7F2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '0.75rem'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <div
                style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '10px',
                  backgroundColor: 'rgba(95, 155, 104, 0.15)',
                  color: 'var(--primary-green)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                <Sparkles size={18} />
              </div>
              <div>
                <div style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--text-primary)' }}>
                  TravelTrack Context-Aware Agent
                </div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  Connected to your trips, itineraries, expenses, and OpenStreetMap Explore
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              {userTrips.length > 0 && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.82rem' }}>
                  <span style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>Active Trip Context:</span>
                  <select
                    value={selectedTripId}
                    onChange={(e) => setSelectedTripId(e.target.value)}
                    style={{
                      padding: '0.35rem 0.65rem',
                      borderRadius: '8px',
                      border: '1px solid var(--border-soft)',
                      backgroundColor: 'var(--bg-card)',
                      fontSize: '0.82rem',
                      color: 'var(--text-primary)',
                      maxWidth: '240px'
                    }}
                  >
                    <option value="">All Trips / General</option>
                    {userTrips.map((t) => (
                      <option key={t._id || t.trip_id} value={t._id || t.trip_id}>
                        {t.title} ({t.destination})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={handleClearChatSession}
                title="Clear conversation history"
                style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', padding: '0.4rem 0.75rem' }}
              >
                <Trash2 size={13} />
                <span>Clear</span>
              </button>
            </div>
          </div>

          {/* Quick Action Suggestion Chips */}
          <div
            style={{
              padding: '0.75rem 1.5rem',
              borderBottom: '1px solid var(--border-soft)',
              backgroundColor: 'rgba(0,0,0,0.015)',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              overflowX: 'auto',
              whiteSpace: 'nowrap'
            }}
          >
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Quick Suggestions:
            </span>
            {[
              { label: '💰 Check my budget', text: 'How much budget do I have left?' },
              { label: '📍 Find places in Hyderabad', text: 'Find top attractions in Hyderabad' },
              { label: '📅 What am I doing on Day 1?', text: 'What am I doing on Day 1?' },
              { label: '🧾 Add ₹1,200 for dinner', text: 'Add an expense of ₹1,200 for dinner' },
              { label: '✨ Check my wishlist', text: 'Check my wishlist' },
              { label: '🧳 Read my trips', text: 'Read my trips' }
            ].map((chip, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleSendChatMessage(chip.text)}
                style={{
                  padding: '0.35rem 0.75rem',
                  borderRadius: '999px',
                  border: '1px solid var(--border-soft)',
                  backgroundColor: 'var(--bg-card)',
                  color: 'var(--text-primary)',
                  fontSize: '0.78rem',
                  fontWeight: 500,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  flexShrink: 0
                }}
              >
                {chip.label}
              </button>
            ))}
          </div>

          {/* Chat Messages Stream */}
          <div
            style={{
              flex: 1,
              overflowY: 'auto',
              padding: '1.75rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '1.25rem',
              maxHeight: '560px'
            }}
          >
            {chatMessages.length === 0 ? (
              <div style={{ textAlign: 'center', margin: 'auto 0', padding: '2rem 1rem', maxWidth: '580px', alignSelf: 'center' }}>
                <div
                  style={{
                    width: '56px',
                    height: '56px',
                    borderRadius: '50%',
                    backgroundColor: 'rgba(95, 155, 104, 0.12)',
                    color: 'var(--primary-green)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    margin: '0 auto 1rem'
                  }}
                >
                  <Sparkles size={28} />
                </div>
                <h3 style={{ fontSize: '1.35rem', fontWeight: 700, marginBottom: '0.6rem', color: 'var(--text-primary)' }}>
                  Ready to assist your journeys
                </h3>
                <p style={{ fontSize: '0.92rem', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: '1.5rem' }}>
                  I can check your real budgets, inspect itineraries, discover authentic OpenStreetMap places, add activities, log expenses, and update trips.
                </p>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0.75rem', textAlign: 'left' }}>
                  <div style={{ padding: '0.85rem', borderRadius: '10px', backgroundColor: 'var(--bg-main)', border: '1px solid var(--border-soft)' }}>
                    <div style={{ fontWeight: 600, fontSize: '0.84rem', color: 'var(--primary-green)', marginBottom: '0.25rem' }}>
                      📍 Explore & Schedule
                    </div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                      "Find sights in Tokyo" followed by "Add the first one to Day 2".
                    </div>
                  </div>
                  <div style={{ padding: '0.85rem', borderRadius: '10px', backgroundColor: 'var(--bg-main)', border: '1px solid var(--border-soft)' }}>
                    <div style={{ fontWeight: 600, fontSize: '0.84rem', color: 'var(--primary-green)', marginBottom: '0.25rem' }}>
                      💰 Budgets & Expenses
                    </div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                      "How much do I have left?" or "Add an expense of ₹500 for taxi".
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              chatMessages.map((m) => (
                <div
                  key={m.id}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: m.role === 'user' ? 'flex-end' : 'flex-start',
                    width: '100%'
                  }}
                >
                  <div
                    style={{
                      maxWidth: '82%',
                      padding: '1rem 1.25rem',
                      borderRadius: m.role === 'user' ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
                      backgroundColor: m.role === 'user' ? 'var(--primary-green, #5F9B68)' : 'var(--bg-main, #FAF7F2)',
                      color: m.role === 'user' ? '#FFFFFF' : 'var(--text-primary, #2A2A2A)',
                      border: m.role === 'user' ? 'none' : '1px solid var(--border-soft, #D8CFBE)',
                      boxShadow: '0 2px 8px rgba(0,0,0,0.03)',
                      fontSize: '0.92rem',
                      lineHeight: 1.6,
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word'
                    }}
                  >
                    {/* Tool Badge */}
                    {m.tool_called && (
                      <div
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.35rem',
                          fontSize: '0.75rem',
                          padding: '0.2rem 0.5rem',
                          borderRadius: '4px',
                          backgroundColor: 'rgba(95, 155, 104, 0.15)',
                          color: 'var(--primary-green)',
                          fontWeight: 600,
                          marginBottom: '0.6rem'
                        }}
                      >
                        <CheckCircle2 size={12} />
                        <span>Action: {m.tool_called}</span>
                      </div>
                    )}

                    {m.content}

                    {/* Places recommendation cards */}
                    {m.places && m.places.length > 0 && (
                      <div style={{ marginTop: '1rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0.75rem' }}>
                        {m.places.slice(0, 4).map((p, pIdx) => (
                          <div
                            key={p.id || pIdx}
                            style={{
                              padding: '0.65rem',
                              borderRadius: '10px',
                              backgroundColor: 'var(--bg-card)',
                              border: '1px solid var(--border-soft)',
                              display: 'flex',
                              gap: '0.65rem'
                            }}
                          >
                            {p.image_url ? (
                              <div style={{ width: '56px', height: '56px', borderRadius: '8px', overflow: 'hidden', flexShrink: 0 }}>
                                <SafeImage src={p.image_url} alt={p.name} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                              </div>
                            ) : (
                              <div style={{ width: '56px', height: '56px', borderRadius: '8px', backgroundColor: 'rgba(95,155,104,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--primary-green)', flexShrink: 0 }}>
                                <MapPin size={20} />
                              </div>
                            )}
                            <div style={{ overflow: 'hidden' }}>
                              <div style={{ fontWeight: 600, fontSize: '0.84rem', color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                {p.name}
                              </div>
                              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                {p.category || 'Sight'} • {p.address || p.location || ''}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Confirmation Action Card */}
                    {m.pending_action && (
                      <div
                        style={{
                          marginTop: '1rem',
                          padding: '0.85rem 1rem',
                          borderRadius: '10px',
                          backgroundColor: 'rgba(239, 68, 68, 0.08)',
                          border: '1px solid rgba(239, 68, 68, 0.25)'
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', color: '#B91C1C', fontWeight: 600, fontSize: '0.86rem', marginBottom: '0.6rem' }}>
                          <AlertTriangle size={15} />
                          <span>Action Confirmation Required</span>
                        </div>
                        <div style={{ display: 'flex', gap: '0.6rem' }}>
                          <button
                            type="button"
                            className="btn btn-primary btn-sm"
                            style={{ backgroundColor: '#B91C1C', borderColor: '#B91C1C', padding: '0.4rem 0.85rem', fontSize: '0.82rem' }}
                            onClick={() => handleSendChatMessage(null, true)}
                            disabled={chatLoading}
                          >
                            Confirm Action
                          </button>
                          <button
                            type="button"
                            className="btn btn-secondary btn-sm"
                            style={{ padding: '0.4rem 0.85rem', fontSize: '0.82rem' }}
                            onClick={() => handleSendChatMessage(null, false)}
                            disabled={chatLoading}
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

            {chatLoading && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.85rem 1.25rem',
                  borderRadius: '18px 18px 18px 4px',
                  backgroundColor: 'var(--bg-main)',
                  border: '1px solid var(--border-soft)',
                  color: 'var(--text-secondary)',
                  fontSize: '0.86rem',
                  width: 'fit-content'
                }}
              >
                <RefreshCw size={14} className="spinner" />
                <span>AI is reading context and executing tool...</span>
              </div>
            )}

            <div ref={chatEndRef} />
          </div>

          {/* Chat Input Console */}
          <div
            style={{
              padding: '1rem 1.5rem',
              borderTop: '1px solid var(--border-soft)',
              backgroundColor: 'var(--bg-main, #FAF7F2)',
              display: 'flex',
              gap: '0.75rem',
              alignItems: 'center'
            }}
          >
            <input
              type="text"
              className="input-field"
              placeholder="Ask AI or instruct an action (e.g. 'Add Charminar to Day 2', 'How much budget left?')..."
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendChatMessage();
                }
              }}
              disabled={chatLoading}
              style={{
                flex: 1,
                padding: '0.75rem 1rem',
                fontSize: '0.9rem',
                borderRadius: '10px',
                border: '1px solid var(--border-soft)',
                backgroundColor: 'var(--bg-card)'
              }}
            />
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => handleSendChatMessage()}
              disabled={chatLoading || !chatInput.trim()}
              style={{
                padding: '0.75rem 1.25rem',
                borderRadius: '10px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.45rem'
              }}
            >
              <Send size={15} />
              <span>Send</span>
            </button>
          </div>
        </div>
      ) : (
        <div className="ai-planner-grid">
          {/* Left Form Panel */}
          <div className="card ai-form-card">
            <div className="form-header" style={{ marginBottom: '1.5rem' }}>
              <div className="editorial-mark"><i></i> PARAMETERS</div>
              <h3 style={{ fontSize: '1.5rem' }}>Trip Preferences</h3>
          </div>

          <form onSubmit={handleGenerate}>
            {/* Anchor Landmark Banner if present */}
            {formData.anchor_place_name && (
              <div
                style={{
                  background: 'rgba(95, 155, 104, 0.12)',
                  border: '1px solid var(--primary-green)',
                  borderRadius: 'var(--radius-md)',
                  padding: '0.65rem 0.85rem',
                  marginBottom: '1.25rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '0.5rem',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                  <Sparkles size={14} style={{ color: 'var(--primary-green)' }} />
                  <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                    Anchored around: <strong>{formData.anchor_place_name}</strong>
                  </span>
                </div>
                <button
                  type="button"
                  onClick={handleClearAnchor}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)' }}
                  title="Clear anchor"
                >
                  <X size={13} />
                </button>
              </div>
            )}

            <div className="form-group">
              <label className="form-label" htmlFor="ai-destination">
                DESTINATION <span style={{ color: 'var(--accent)' }}>*</span>
              </label>
              <input
                id="ai-destination"
                type="text"
                className="form-input"
                placeholder="e.g. Hyderabad, Bengaluru, Goa, Paris"
                value={formData.destination}
                onChange={(e) => setFormData({ ...formData, destination: e.target.value })}
                required
              />
            </div>

            <div className="form-grid-two">
              <div className="form-group">
                <label className="form-label" htmlFor="ai-days">
                  DURATION (DAYS)
                </label>
                <input
                  id="ai-days"
                  type="number"
                  min="1"
                  max="30"
                  className="form-input"
                  value={formData.days}
                  onChange={(e) => setFormData({ ...formData, days: e.target.value })}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="ai-start-date">
                  START DATE
                </label>
                <input
                  id="ai-start-date"
                  type="date"
                  className="form-input"
                  value={formData.start_date}
                  onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                />
              </div>
            </div>

            <div className="form-grid-two">
              <div className="form-group">
                <label className="form-label" htmlFor="ai-travelers">
                  TRAVELERS
                </label>
                <input
                  id="ai-travelers"
                  type="number"
                  min="1"
                  max="50"
                  className="form-input"
                  value={formData.travelers}
                  onChange={(e) => setFormData({ ...formData, travelers: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="ai-budget">
                  BUDGET CAP (USD)
                </label>
                <input
                  id="ai-budget"
                  type="number"
                  step="any"
                  min="0"
                  className="form-input"
                  placeholder="e.g. 2500"
                  value={formData.budget}
                  onChange={(e) => setFormData({ ...formData, budget: e.target.value })}
                />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="ai-style">
                TRAVEL STYLE
              </label>
              <select
                id="ai-style"
                className="form-select"
                value={formData.travel_style}
                onChange={(e) => setFormData({ ...formData, travel_style: e.target.value })}
              >
                {STYLE_OPTIONS.map((style) => (
                  <option key={style} value={style}>
                    {style}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">INTERESTS &amp; ACTIVITIES</label>
              <div className="interest-tags-container">
                {INTEREST_OPTIONS.map((interest) => {
                  const isSelected = formData.interests.includes(interest);
                  return (
                    <button
                      key={interest}
                      type="button"
                      className={`interest-tag-btn ${isSelected ? 'selected' : ''}`}
                      onClick={() => toggleInterest(interest)}
                    >
                      {isSelected && <CheckCircle2 size={12} />}
                      <span>{interest}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              style={{ width: '100%', marginTop: '1rem' }}
              disabled={generating}
            >
              {generating ? (
                <>
                  <span className="spinner" />
                  <span>Curating Grounded Itinerary...</span>
                </>
              ) : (
                <>
                  <Sparkles size={15} />
                  <span>Generate Grounded Itinerary</span>
                </>
              )}
            </button>
          </form>
        </div>

        {/* Right Output Panel */}
        <div className="ai-output-panel">
          {generating ? (
            <div className="card" style={{ padding: '4rem 2rem', textAlign: 'center' }}>
              <div className="spinner spinner-lg" style={{ margin: '0 auto 1.5rem' }} />
              <h3>Analyzing real OpenStreetMap landmarks &amp; routes...</h3>
              <p style={{ color: 'var(--text-secondary)', maxWidth: '440px', margin: '0.5rem auto 0' }}>
                Clustering verified places in {formData.destination || 'your destination'} by geographic proximity to minimize transit time.
              </p>
            </div>
          ) : generatedPlan ? (
            <div className="ai-plan-results">
              {/* Header Card */}
              <div className="card" style={{ marginBottom: '1.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem', marginBottom: '1rem' }}>
                  <div>
                    <div className="editorial-mark"><i></i> GROUNDED ITINERARY</div>
                    <h2 style={{ fontSize: '2rem' }}>{generatedPlan.destination}</h2>
                    <p style={{ color: 'var(--text-secondary)', marginTop: '0.4rem', fontSize: '0.95rem' }}>
                      {generatedPlan.summary}
                    </p>
                  </div>

                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={handleSaveAsTrip}
                    disabled={savingTrip}
                  >
                    {savingTrip ? (
                      <>
                        <span className="spinner" />
                        <span>Saving Trip...</span>
                      </>
                    ) : (
                      <>
                        <BookmarkPlus size={15} />
                        <span>Save to My Trips</span>
                      </>
                    )}
                  </button>
                </div>

                {/* Itinerary Rationale Box */}
                {generatedPlan.itinerary_rationale && (
                  <div
                    style={{
                      background: 'var(--surface, #f8f9f6)',
                      borderLeft: '3px solid var(--primary-green)',
                      padding: '0.75rem 1rem',
                      borderRadius: '0 var(--radius-sm) var(--radius-sm) 0',
                      fontSize: '0.85rem',
                      color: 'var(--text-primary)',
                      lineHeight: '1.5',
                      marginBottom: '1rem',
                    }}
                  >
                    <strong>Route Strategy:</strong> {generatedPlan.itinerary_rationale}
                  </div>
                )}

                {/* Estimated Budget Cards */}
                {generatedPlan.budget_breakdown && (
                  <div className="category-breakdown-row" style={{ marginTop: '0.75rem' }}>
                    {Object.entries(generatedPlan.budget_breakdown).map(([cat, amt]) => (
                      <div key={cat} className="category-pill">
                        <span className="cat-name">{cat}</span>
                        <span className="cat-amount">{formatCurrency(amt)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Day-by-Day Selector */}
              <div className="ai-day-tabs">
                {generatedPlan.itinerary.map((dayPlan, idx) => (
                  <button
                    key={dayPlan.day}
                    type="button"
                    className={`ai-day-tab ${activeDayIndex === idx ? 'active' : ''}`}
                    onClick={() => setActiveDayIndex(idx)}
                  >
                    DAY {dayPlan.day}
                  </button>
                ))}
              </div>

              {/* Active Day Activities */}
              {generatedPlan.itinerary[activeDayIndex] && (
                <div className="card" style={{ marginBottom: '1.5rem' }}>
                  <div style={{ borderBottom: '1px solid var(--border)', paddingBottom: '0.85rem', marginBottom: '1.25rem' }}>
                    <div className="editorial-mark">
                      <i></i> DAY {generatedPlan.itinerary[activeDayIndex].day}
                    </div>
                    <h3 style={{ fontSize: '1.35rem', margin: '0.25rem 0' }}>
                      {generatedPlan.itinerary[activeDayIndex].theme}
                    </h3>
                    {generatedPlan.itinerary[activeDayIndex].rationale && (
                      <p style={{ color: 'var(--text-secondary)', fontSize: '0.82rem', margin: '0.35rem 0 0 0', lineHeight: 1.4 }}>
                        {generatedPlan.itinerary[activeDayIndex].rationale}
                      </p>
                    )}
                  </div>

                  <div className="timeline-activities-list">
                    {generatedPlan.itinerary[activeDayIndex].activities?.map((act, aIdx) => (
                      <div key={aIdx} className="timeline-activity-card">
                        <div className="activity-time-col">
                          <Clock size={13} style={{ color: 'var(--primary-green)' }} />
                          <span>{act.time}</span>
                        </div>
                        <div className="activity-content-col">
                          <div className="activity-header-row" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                              <h4 className="activity-title" style={{ margin: 0 }}>{act.title}</h4>
                              {act.category && (
                                <span className={`place-category-badge cat-${act.category.toLowerCase()}`} style={{ fontSize: '0.65rem' }}>
                                  {act.category.toUpperCase()}
                                </span>
                              )}
                              {act.distance_km !== null && act.distance_km !== undefined && (
                                <span
                                  style={{
                                    fontFamily: 'var(--font-mono)',
                                    fontSize: '0.7rem',
                                    color: 'var(--primary-green)',
                                    background: 'rgba(95, 155, 104, 0.1)',
                                    padding: '1px 6px',
                                    borderRadius: '3px',
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '3px',
                                  }}
                                >
                                  <Navigation size={9} />
                                  <span>{formatDistance(act.distance_km)}</span>
                                </span>
                              )}
                            </div>
                            {act.estimated_cost > 0 && (
                              <span className="activity-cost-tag">
                                {formatCurrency(act.estimated_cost)}
                              </span>
                            )}
                          </div>
                          {act.location && (
                            <div className="activity-location" style={{ marginTop: '0.35rem' }}>
                              <MapPin size={12} />
                              <span>{act.location}</span>
                            </div>
                          )}
                          <p className="activity-desc" style={{ marginTop: '0.4rem', fontSize: '0.85rem', lineHeight: '1.45' }}>
                            {act.description}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Packing List & Travel Tips */}
              <div className="form-grid-two">
                <div className="card">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                    <Briefcase size={16} style={{ color: 'var(--primary-green)' }} />
                    <h4 style={{ margin: 0, fontSize: '1.15rem' }}>Packing Checklist</h4>
                  </div>
                  <ul className="advice-tips-list">
                    {generatedPlan.packing_list?.map((item, idx) => (
                      <li key={idx}>
                        <CheckCircle2 size={13} style={{ color: 'var(--primary-green)', flexShrink: 0, marginTop: '3px' }} />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="card">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                    <Lightbulb size={16} style={{ color: 'var(--primary-green)' }} />
                    <h4 style={{ margin: 0, fontSize: '1.15rem' }}>Local Travel Tips</h4>
                  </div>
                  <ul className="advice-tips-list">
                    {generatedPlan.travel_tips?.map((tip, idx) => (
                      <li key={idx}>
                        <Compass size={13} style={{ color: 'var(--primary-green)', flexShrink: 0, marginTop: '3px' }} />
                        <span>{tip}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          ) : (
            <div className="card empty-ai-placeholder">
              <div className="empty-icon-wrapper">
                <Sparkles size={24} />
              </div>
              <h3 className="empty-title">Ready to plan your escape?</h3>
              <p className="empty-desc">
                Fill out the preferences on the left to generate a realistic travel itinerary analyzing real OpenStreetMap sights, distances, and pacing.
              </p>
            </div>
          )}
        </div>
      </div>
      )}
    </div>
  );
};
