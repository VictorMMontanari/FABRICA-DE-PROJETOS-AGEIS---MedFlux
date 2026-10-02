import { Send, Sparkles, User } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { TriageResultCard } from '../components/TriageResultCard'
import { sendTriageMessage, type TriageRecommendation } from '../services/api'
import { getStoredSession } from '../services/session'

type ChatRole = 'assistant' | 'user'

type ChatMessage = {
  id: string
  role: ChatRole
  content: string
  timestamp: string
  triageRecommendation?: TriageRecommendation | null
}

function makeSessionId() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }

  return `session-${Date.now()}`
}

function getCurrentTime() {
  return new Intl.DateTimeFormat('pt-BR', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date())
}

export function ChatTriagePage() {
  const session = getStoredSession()
  const sessionId = useMemo(() => makeSessionId(), [])
  const [inputValue, setInputValue] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome-1',
      role: 'assistant',
      content:
        'Olá, Marina. Sou a Clara, sua assistente de saúde. Conte quais sintomas você está sentindo e vou te orientar com a triagem inicial.',
      timestamp: 'Agora',
    },
  ])
  const endRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const trimmedValue = inputValue.trim()

    if (!trimmedValue || isSending) {
      return
    }

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: trimmedValue,
      timestamp: getCurrentTime(),
    }

    setMessages((current) => [...current, userMessage])
    setInputValue('')
    setIsSending(true)

    try {
      const response = await sendTriageMessage({
        session_id: sessionId,
        message: trimmedValue,
      })

      setMessages((current) => [
        ...current,
        {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: response.reply,
          timestamp: response.timestamp,
          triageRecommendation: response.triage_recommendation,
        },
      ])
    } finally {
      setIsSending(false)
    }
  }

  return (
    <section className="page-card chat-shell">
      <header className="chat-topbar">
        <div>
          <h1 className="section-title">Assistente de saúde online</h1>
          <p className="section-subtitle">Triagem conversacional com apoio da Clara.</p>
        </div>
        <div className="presence-pill">
          <span className="presence-pill__dot" />
          Online para ajudar agora
        </div>
      </header>

      <div className="chat-messages" id="chat-history">
        {messages.length === 0 ? (
          <div className="chat-empty-state">
            <div>
              <Sparkles size={28} />
              <p>Envie uma mensagem para começar a triagem.</p>
            </div>
          </div>
        ) : null}

        {messages.map((message) => (
          <article
            key={message.id}
            className={`chat-bubble${message.role === 'user' ? ' chat-bubble--user' : ' chat-bubble--assistant'}`}
          >
            <div className="chat-bubble__head">
              <div
                className={`chat-bubble__avatar${message.role === 'user' ? ' chat-bubble__avatar--user' : ' chat-bubble__avatar--assistant'}`}
              >
                {message.role === 'user' ? <User size={16} /> : <Sparkles size={16} />}
              </div>
              <strong>{message.role === 'user' ? session?.user.name ?? 'Paciente' : 'Clara'}</strong>
            </div>
            <div className="chat-bubble__content">{message.content}</div>
            <div className="chat-bubble__timestamp">{message.timestamp}</div>

            {message.triageRecommendation?.required ? (
              <TriageResultCard recommendation={message.triageRecommendation} />
            ) : null}
          </article>
        ))}

        <div ref={endRef} />
      </div>

      <footer className="chat-composer">
        <form className="composer-form" onSubmit={handleSubmit}>
          <textarea
            className="composer-input"
            placeholder="Escreva uma mensagem..."
            value={inputValue}
            onChange={(event) => setInputValue(event.target.value)}
            rows={1}
          />
          <button type="submit" className="composer-button" disabled={isSending} aria-label="Enviar mensagem">
            <Send size={18} />
          </button>
        </form>
      </footer>
    </section>
  )
}