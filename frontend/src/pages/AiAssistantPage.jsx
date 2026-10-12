import { useState, useEffect, useRef } from 'react'
import {
  Sparkles, Send, Trash2, ShieldCheck, AlertCircle, RefreshCw,
  Copy, Check, Bot, User, ArrowUpRight, Heart, Info, Clock, ExternalLink
} from 'lucide-react'
import api from '../lib/api'
import { useAuth } from '../context/AuthContext'

function formatMessageContent(text) {
  if (!text) return ''
  // Basic markdown formatting helper for bold, list items, and paragraph breaks
  const paragraphs = text.split('\n\n')
  return paragraphs.map((para, pIdx) => {
    const lines = para.split('\n')
    const isBulletList = lines.every(l => l.trim().startsWith('- ') || l.trim().startsWith('* ') || /^\d+\.\s/.test(l.trim()))

    if (isBulletList) {
      return (
        <ul key={pIdx} style={{ margin: '8px 0', paddingLeft: 20 }}>
          {lines.map((line, lIdx) => {
            const clean = line.replace(/^[-*]\s+|\d+\.\s+/, '')
            return (
              <li key={lIdx} style={{ marginBottom: 4, lineHeight: 1.55 }}>
                {renderFormattedSpan(clean)}
              </li>
            )
          })}
        </ul>
      )
    }

    return (
      <p key={pIdx} style={{ margin: '6px 0', lineHeight: 1.55 }}>
        {lines.map((line, lIdx) => (
          <span key={lIdx}>
            {renderFormattedSpan(line)}
            {lIdx < lines.length - 1 && <br />}
          </span>
        ))}
      </p>
    )
  })
}

function renderFormattedSpan(str) {
  // Bold formatting **text**
  const parts = str.split(/(\*\*.*?\*\*)/g)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i} style={{ color: 'var(--text)', fontWeight: 700 }}>{part.slice(2, -2)}</strong>
    }
    return part
  })
}

export default function AiAssistantPage() {
  const { user } = useAuth()
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingHistory, setLoadingHistory] = useState(true)
  const [prompts, setPrompts] = useState([])
  const [copiedIndex, setCopiedIndex] = useState(null)
  const [errorBanner, setErrorBanner] = useState(null)
  const [lastFailedMessage, setLastFailedMessage] = useState(null)

  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, loading])

  // Load history and suggested prompts on mount
  useEffect(() => {
    let isMounted = true
    setLoadingHistory(true)

    Promise.all([
      api.get('/assistant/history').then(r => r.data?.messages || []).catch(() => []),
      api.get('/assistant/prompts').then(r => r.data?.prompts || []).catch(() => []),
    ]).then(([historyMessages, suggestedPrompts]) => {
      if (!isMounted) return
      setMessages(historyMessages)
      setPrompts(suggestedPrompts)
    }).finally(() => {
      if (isMounted) setLoadingHistory(false)
    })

    return () => { isMounted = false }
  }, [])

  const handleSend = async (textToSend) => {
    const text = (textToSend || input).trim()
    if (!text || loading) return

    setInput('')
    setErrorBanner(null)
    setLastFailedMessage(null)

    // Optimistically append user message
    const tempUserMsg = {
      role: 'user',
      content: text,
      createdAt: new Date().toISOString(),
    }
    setMessages(prev => [...prev, tempUserMsg])
    setLoading(true)

    try {
      const res = await api.post('/assistant/chat', { message: text })
      const assistantMsg = {
        role: 'assistant',
        content: res.data.reply,
        provider: res.data.provider,
        model: res.data.model,
        createdAt: res.data.timestamp || new Date().toISOString(),
      }
      setMessages(prev => [...prev, assistantMsg])
    } catch (err) {
      console.error('Chat error:', err)
      const errorMsg = err.response?.data?.message || 'Failed to receive response from AI Health Assistant.'
      setErrorBanner(errorMsg)
      setLastFailedMessage(text)
    } finally {
      setLoading(false)
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleClearHistory = async () => {
    if (!window.confirm('Are you sure you want to clear your AI Assistant conversation history?')) return
    try {
      await api.delete('/assistant/history')
      setMessages([])
      setErrorBanner(null)
    } catch (err) {
      console.error('Clear history error:', err)
    }
  }

  const handleCopy = (text, idx) => {
    navigator.clipboard.writeText(text)
    setCopiedIndex(idx)
    setTimeout(() => setCopiedIndex(null), 2000)
  }

  const patientFirstName = user?.name?.split(' ')[0] || 'Patient'

  return (
    <div className="fade-in" style={{ maxWidth: 1040, margin: '0 auto', height: 'calc(100vh - 84px)', display: 'flex', flexDirection: 'column' }}>
      {/* ── Page Header ──────────────────────────────────────────────── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: 12, borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
            <div style={{
              width: 32, height: 32, borderRadius: 8,
              background: 'linear-gradient(135deg, var(--brand), var(--accent))',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: 'var(--shadow)'
            }}>
              <Sparkles size={18} color="white" />
            </div>
            <div>
              <h2 style={{ fontSize: 18, fontWeight: 800, margin: 0, fontFamily: 'Outfit', display: 'flex', alignItems: 'center', gap: 8 }}>
                AI Health Assistant
                <span style={{
                  fontSize: 10, fontWeight: 700, padding: '2px 7px', borderRadius: 99,
                  background: 'var(--brand-glow)', color: 'var(--brand)', border: '1px solid var(--border)'
                }}>
                  Personalized
                </span>
              </h2>
              <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 1 }}>
                Conversational health intelligence grounded in your MediTwin clinical twin
              </div>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 6,
            fontSize: 11, color: 'var(--muted)', background: 'var(--surface-2)',
            padding: '5px 10px', borderRadius: 6, border: '1px solid var(--border)'
          }}>
            <ShieldCheck size={14} color="var(--brand)" />
            <span>Encrypted & Patient-Isolated</span>
          </div>

          {messages.length > 0 && (
            <button
              onClick={handleClearHistory}
              className="btn btn-ghost"
              style={{ fontSize: 12, padding: '5px 10px', color: 'var(--muted)' }}
              title="Clear conversation history"
            >
              <Trash2 size={13} />
              <span>Clear Chat</span>
            </button>
          )}
        </div>
      </div>

      {/* ── Safety & Medical Disclaimer Banner ────────────────────────── */}
      <div style={{
        marginTop: 10, marginBottom: 10,
        padding: '8px 12px', borderRadius: 'var(--radius)',
        background: 'rgba(217,119,6,0.08)', border: '1px solid rgba(217,119,6,0.25)',
        display: 'flex', alignItems: 'flex-start', gap: 9, flexShrink: 0
      }}>
        <Info size={16} style={{ color: 'var(--warning)', marginTop: 2, flexShrink: 0 }} />
        <div style={{ fontSize: 11.5, color: 'var(--text)', lineHeight: 1.45 }}>
          <strong>Clinical Decision Support Disclaimer:</strong> MediTwin AI is an informational decision-support assistant, <strong>not a medical doctor</strong>. It explains your recorded diagnostic test results, risk calculations, and symptoms. It does not prescribe medications or independently diagnose conditions. For emergencies, please dial <strong>911, 112</strong> or contact your nearest emergency medical facility immediately.
        </div>
      </div>

      {/* ── Chat Messages Scroll Area ─────────────────────────────────── */}
      <div style={{
        flex: 1, overflowY: 'auto', padding: '12px 4px',
        display: 'flex', flexDirection: 'column', gap: 14
      }}>
        {loadingHistory ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--muted)', gap: 8, fontSize: 13 }}>
            <RefreshCw size={16} className="spin" />
            <span>Loading conversation and health context...</span>
          </div>
        ) : messages.length === 0 ? (
          <div style={{
            margin: 'auto', textAlign: 'center', maxWidth: 540,
            padding: '30px 20px', background: 'var(--surface)',
            borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)',
            boxShadow: 'var(--shadow)'
          }}>
            <div style={{
              width: 50, height: 50, borderRadius: 14,
              background: 'linear-gradient(135deg, var(--brand), var(--brand-2))',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 14px', boxShadow: 'var(--shadow-md)'
            }}>
              <Bot size={26} color="white" />
            </div>

            <h3 style={{ fontSize: 17, fontWeight: 700, margin: '0 0 6px', fontFamily: 'Outfit' }}>
              Hello, {patientFirstName}! How can I assist you today?
            </h3>
            <p style={{ fontSize: 13, color: 'var(--muted)', margin: '0 0 20px', lineHeight: 1.5 }}>
              I have secure access to your MediTwin biomarkers, 90-day acute event risk calculations, DDXPlus symptom differential, and clinical recommendations. Ask me any question about your results!
            </p>

            {prompts.length > 0 && (
              <div>
                <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 10 }}>
                  Suggested Questions For Your Record
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {prompts.map((p, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSend(p)}
                      style={{
                        padding: '9px 14px', borderRadius: 'var(--radius)',
                        background: 'var(--surface-2)', border: '1px solid var(--border)',
                        color: 'var(--text)', fontSize: 12.5, textAlign: 'left',
                        cursor: 'pointer', transition: 'all 0.15s ease',
                        display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8
                      }}
                      onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--brand)'; e.currentTarget.style.background = 'var(--surface)' }}
                      onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.background = 'var(--surface-2)' }}
                    >
                      <span>{p}</span>
                      <ArrowUpRight size={14} color="var(--brand)" style={{ flexShrink: 0 }} />
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <>
            {messages.map((msg, idx) => {
              const isUser = msg.role === 'user'
              const timeStr = msg.createdAt
                ? new Date(msg.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                : ''

              return (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    flexDirection: isUser ? 'row-reverse' : 'row',
                    alignItems: 'flex-start',
                    gap: 10,
                  }}
                >
                  {/* Avatar */}
                  <div style={{
                    width: 32, height: 32, borderRadius: 8,
                    background: isUser ? 'var(--brand)' : 'var(--surface-2)',
                    border: isUser ? 'none' : '1px solid var(--border)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    flexShrink: 0, marginTop: 2,
                    boxShadow: isUser ? 'var(--shadow)' : 'none'
                  }}>
                    {isUser ? (
                      <User size={16} color="white" />
                    ) : (
                      <Bot size={17} color="var(--brand)" />
                    )}
                  </div>

                  {/* Message Bubble Container */}
                  <div style={{
                    maxWidth: '82%',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: isUser ? 'flex-end' : 'flex-start'
                  }}>
                    <div style={{
                      padding: '11px 15px',
                      borderRadius: isUser ? '14px 4px 14px 14px' : '4px 14px 14px 14px',
                      background: isUser ? 'var(--brand)' : 'var(--surface)',
                      color: isUser ? '#ffffff' : 'var(--text)',
                      border: isUser ? 'none' : '1px solid var(--border)',
                      fontSize: 13.5,
                      boxShadow: 'var(--shadow)',
                      wordBreak: 'break-word',
                    }}>
                      {isUser ? (
                        <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>{msg.content}</div>
                      ) : (
                        <div>
                          {formatMessageContent(msg.content)}
                        </div>
                      )}
                    </div>

                    {/* Metadata & Actions */}
                    <div style={{
                      display: 'flex', alignItems: 'center', gap: 8,
                      marginTop: 4, padding: '0 4px', fontSize: 11, color: 'var(--muted)'
                    }}>
                      <span>{timeStr}</span>

                      {!isUser && msg.provider && (
                        <span style={{
                          fontSize: 10, background: 'var(--surface-2)',
                          padding: '1px 6px', borderRadius: 4, border: '1px solid var(--border)',
                          color: 'var(--muted)'
                        }}>
                          {msg.provider}
                        </span>
                      )}

                      {!isUser && (
                        <button
                          onClick={() => handleCopy(msg.content, idx)}
                          style={{
                            background: 'transparent', border: 'none',
                            color: 'var(--muted)', cursor: 'pointer',
                            display: 'flex', alignItems: 'center', gap: 3, padding: '1px 4px'
                          }}
                          title="Copy text"
                        >
                          {copiedIndex === idx ? (
                            <>
                              <Check size={11} color="var(--brand)" />
                              <span style={{ color: 'var(--brand)', fontSize: 10 }}>Copied</span>
                            </>
                          ) : (
                            <Copy size={11} />
                          )}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}

            {/* Typing / Loading indicator */}
            {loading && (
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                <div style={{
                  width: 32, height: 32, borderRadius: 8,
                  background: 'var(--surface-2)', border: '1px solid var(--border)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  flexShrink: 0
                }}>
                  <Bot size={17} color="var(--brand)" />
                </div>
                <div style={{
                  padding: '12px 16px', borderRadius: '4px 14px 14px 14px',
                  background: 'var(--surface)', border: '1px solid var(--border)',
                  boxShadow: 'var(--shadow)', display: 'flex', alignItems: 'center', gap: 8
                }}>
                  <div style={{ display: 'flex', gap: 4 }}>
                    <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--brand)', animation: 'pulseDot 1.4s infinite ease-in-out' }} />
                    <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--brand)', animation: 'pulseDot 1.4s infinite ease-in-out 0.2s' }} />
                    <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--brand)', animation: 'pulseDot 1.4s infinite ease-in-out 0.4s' }} />
                  </div>
                  <span style={{ fontSize: 12, color: 'var(--muted)' }}>Retrieving clinical context & reasoning...</span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* ── Error Banner & Retry ───────────────────────────────────────── */}
      {errorBanner && (
        <div style={{
          marginBottom: 8, padding: '8px 12px', borderRadius: 'var(--radius)',
          background: 'rgba(220,38,38,0.08)', border: '1px solid rgba(220,38,38,0.25)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, flexShrink: 0
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: 'var(--danger)' }}>
            <AlertCircle size={15} style={{ flexShrink: 0 }} />
            <span>{errorBanner}</span>
          </div>
          {lastFailedMessage && (
            <button
              onClick={() => handleSend(lastFailedMessage)}
              className="btn btn-ghost"
              style={{ fontSize: 11, padding: '3px 8px', color: 'var(--danger)', borderColor: 'rgba(220,38,38,0.3)' }}
            >
              Retry
            </button>
          )}
        </div>
      )}

      {/* ── Quick Prompt Chips (above input when messages exist) ───────── */}
      {messages.length > 0 && prompts.length > 0 && !loading && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6,
          overflowX: 'auto', paddingBottom: 8, flexShrink: 0,
          scrollbarWidth: 'none'
        }}>
          <span style={{ fontSize: 11, color: 'var(--muted)', whiteSpace: 'nowrap', marginRight: 2 }}>
            Suggested:
          </span>
          {prompts.slice(0, 3).map((p, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(p)}
              style={{
                background: 'var(--surface)', border: '1px solid var(--border)',
                borderRadius: 99, padding: '4px 10px', fontSize: 11.5,
                color: 'var(--muted)', cursor: 'pointer', whiteSpace: 'nowrap',
                transition: 'all 0.15s'
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--brand)'; e.currentTarget.style.color = 'var(--text)' }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--muted)' }}
            >
              {p}
            </button>
          ))}
        </div>
      )}

      {/* ── Input Bar ─────────────────────────────────────────────────── */}
      <div style={{
        paddingTop: 8, borderTop: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0
      }}>
        <div style={{ flex: 1, position: 'relative' }}>
          <input
            ref={inputRef}
            type="text"
            className="input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Ask a question about your health results (e.g., "Explain my acute risk factors")...`}
            maxLength={1200}
            disabled={loading}
            style={{
              paddingRight: 60,
              fontSize: 13.5,
              borderRadius: 'var(--radius)',
              background: 'var(--surface)'
            }}
          />
          <div style={{
            position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
            fontSize: 10, color: 'var(--muted-2)'
          }}>
            {input.length > 0 ? `${input.length}/1200` : ''}
          </div>
        </div>

        <button
          onClick={() => handleSend()}
          disabled={!input.trim() || loading}
          className="btn btn-primary"
          style={{
            padding: '9px 16px', borderRadius: 'var(--radius)',
            display: 'flex', alignItems: 'center', gap: 6,
            opacity: (!input.trim() || loading) ? 0.6 : 1,
            cursor: (!input.trim() || loading) ? 'not-allowed' : 'pointer'
          }}
        >
          <Send size={15} />
          <span style={{ fontSize: 13 }}>Send</span>
        </button>
      </div>

      <style>{`
        @keyframes pulseDot {
          0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
          40% { opacity: 1; transform: scale(1.1); }
        }
      `}</style>
    </div>
  )
}
