import { RotateCcw, Send, Sparkles, User } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { FormEvent, KeyboardEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import { TriageResultCard } from '../components/TriageResultCard'
import {
  ApiError,
  getConversation,
  getErrorMessage,
  sendTriageMessage,
  type TriageRecommendation,
} from '../services/api'
import { getStoredSession } from '../services/session'

type ChatRole = 'assistant' | 'user'

type ChatMessage = {
  id: string
  role: ChatRole
  content: string
  timestamp: string
  triageRecommendation?: TriageRecommendation | null
  isError?: boolean
}

function getCurrentTime() {
  return new Intl.DateTimeFormat('pt-BR', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date())
}

function buildWelcome(name?: string): ChatMessage {
  const firstName = name?.split(' ')[0]
  return {
    id: 'welcome-1',
    role: 'assistant',
    content: `Olá${firstName ? `, ${firstName}` : ''}. Sou a Clara, sua assistente de saúde. Conte quais sintomas você está sentindo e vou te orientar com a triagem inicial.`,
    timestamp: 'Agora',
  }
}

export function ChatTriagePage() {
  const session = getStoredSession()
  const userName = session?.user.name
  const [searchParams, setSearchParams] = useSearchParams()
  const conversationParam = searchParams.get('conversa')

  // session_id real é o devolvido pelo backend; null = conversa nova
  const [sessionId, setSessionId] = useState<string | null>(conversationParam)
  const [inputValue, setInputValue] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [isLoadingHistory, setIsLoadingHistory] = useState(Boolean(conversationParam))
  const [messages, setMessages] = useState<ChatMessage[]>(() => [buildWelcome(userName)])
  const endRef = useRef<HTMLDivElement | null>(null)

  // Reabre uma conversa vinda do histórico (/chat?conversa=<id>)
  useEffect(() => {
    if (!conversationParam) {
      return
    }

    let active = true
    setIsLoadingHistory(true)

    getConversation(conversationParam)
      .then((conversation) => {
        if (!active) return
        setSessionId(conversation.id)
        setMessages([
          buildWelcome(userName),
          ...conversation.messages.map((message) => ({
            id: message.id,
            role: message.role,
            content: message.content,
            timestamp: message.timestamp,
            triageRecommendation: message.triage_recommendation,
          })),
        ])
      })
      .catch((error: unknown) => {
        if (!active) return
        setSessionId(null)
        setMessages([
          buildWelcome(userName),
          {
            id: 'history-error',
            role: 'assistant',
            content: `${getErrorMessage(error)} Você pode começar uma nova triagem abaixo.`,
            timestamp: getCurrentTime(),
            isError: true,
          },
        ])
      })
      .finally(() => {
        if (active) setIsLoadingHistory(false)
      })

    return () => {
      active = false
    }
  }, [conversationParam, userName])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, isSending])

  function startNewConversation() {
    setSessionId(null)
    setMessages([buildWelcome(userName)])
    if (conversationParam) {
      setSearchParams({}, { replace: true })
    }
  }

  async function submitMessage() {
    const trimmedValue = inputValue.trim()

    if (!trimmedValue || isSending || isLoadingHistory) {
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

      setSessionId(response.session_id)
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
    } catch (error) {
      // 503: o backend já devolve uma orientação segura (procure a UPA / ligue 192)
      const isSafeFallback = error instanceof ApiError && error.status === 503
      setMessages((current) => [
        ...current,
        {
          id: `assistant-error-${Date.now()}`,
          role: 'assistant',
          content: getErrorMessage(error),
          timestamp: getCurrentTime(),
          isError: !isSafeFallback,
        },
      ])
    } finally {
      setIsSending(false)
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void submitMessage()
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      void submitMessage()
    }
  }

  return (
    <section className="page-card chat-shell">
      <header className="chat-topbar">
        <div>
          <h1 className="section-title">Assistente de saúde online</h1>
          <p className="section-subtitle">Triagem conversacional com apoio da Clara.</p>
        </div>
        <div className="chat-topbar__actions">
          <button
            type="button"
            id="chat-new-conversation"
            className="chat-new-button"
            onClick={startNewConversation}
            disabled={isSending}
          >
            <RotateCcw size={14} />
            Nova triagem
          </button>
          <div className="presence-pill">
            <span className="presence-pill__dot" />
            Online para ajudar agora
          </div>
        </div>
      </header>

      <div className="chat-messages" id="chat-history" aria-live="polite">
        {isLoadingHistory ? (
          <div className="chat-empty-state">
            <div>
              <Sparkles size={28} />
              <p>Carregando sua conversa...</p>
            </div>
          </div>
        ) : null}

        {!isLoadingHistory &&
          messages.map((message) => (
            <article
              key={message.id}
              className={`chat-bubble${message.role === 'user' ? ' chat-bubble--user' : ' chat-bubble--assistant'}${message.isError ? ' chat-bubble--error' : ''}`}
            >
              <div className="chat-bubble__head">
                <div
                  className={`chat-bubble__avatar${message.role === 'user' ? ' chat-bubble__avatar--user' : ' chat-bubble__avatar--assistant'}`}
                >
                  {message.role === 'user' ? <User size={16} /> : <Sparkles size={16} />}
                </div>
                <strong>{message.role === 'user' ? userName ?? 'Paciente' : 'Clara'}</strong>
              </div>
              <div className="chat-bubble__content">{message.content}</div>
              <div className="chat-bubble__timestamp">{message.timestamp}</div>

              {message.triageRecommendation?.required ? (
                <TriageResultCard recommendation={message.triageRecommendation} />
              ) : null}
            </article>
          ))}

        {isSending ? (
          <article className="chat-bubble chat-bubble--assistant chat-bubble--typing" aria-label="Clara está digitando">
            <div className="chat-bubble__head">
              <div className="chat-bubble__avatar chat-bubble__avatar--assistant">
                <Sparkles size={16} />
              </div>
              <strong>Clara</strong>
            </div>
            <div className="typing-dots">
              <span />
              <span />
              <span />
            </div>
          </article>
        ) : null}

        <div ref={endRef} />
      </div>

      <footer className="chat-composer">
        <form className="composer-form" onSubmit={handleSubmit}>
          <textarea
            id="chat-input"
            className="composer-input"
            placeholder="Escreva uma mensagem... (Enter envia, Shift+Enter quebra linha)"
            value={inputValue}
            onChange={(event) => setInputValue(event.target.value)}
            onKeyDown={handleKeyDown}
            maxLength={2000}
            rows={1}
            disabled={isLoadingHistory}
          />
          <button
            type="submit"
            id="chat-send"
            className="composer-button"
            disabled={isSending || isLoadingHistory || !inputValue.trim()}
            aria-label="Enviar mensagem"
          >
            <Send size={18} />
          </button>
        </form>
      </footer>
    </section>
  )
}