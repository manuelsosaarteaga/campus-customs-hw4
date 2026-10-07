import { Fragment, useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import { useAuth } from '../auth'
import { useChatResults, type ChatProduct } from '../chatResults'

type Message = {
  role: 'user' | 'assistant'
  content: string
  products?: ChatProduct[]
  resultsTitle?: string
  error?: boolean
  degraded?: boolean
  retryText?: string
  saved?: boolean
}
type SavedMessage = { id: number; role: 'user' | 'assistant'; content: string; products: ChatProduct[] }

const HISTORY_TURNS = 10

// Quick replies: tappable suggestions that change with the page and the conversation.
const STARTER_REPLIES = ['What hoodies do you have?', 'Gifts under $40', 'Residential college gear', 'Harvard–Yale game gear']
const ITEM_REPLIES = ['Is this in stock in M?', 'What colors does it come in?', 'Show me similar items']
const FOLLOW_UP_REPLIES = ['Anything cheaper?', 'Show me navy options', 'Which are in stock in L?']

const greeting = (firstName?: string): Message => ({
  role: 'assistant',
  content: firstName
    ? `Welcome back, ${firstName}! Ask me about hoodies, sizes, prices, or stock — I'll remember our chat.`
    : "Hi! I'm the Campus Customs assistant. Ask me about hoodies, sizes, prices, or stock.",
})

/** Renders **bold** and line breaks (some saved replies use light markdown). */
function formatText(text: string): ReactNode {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith('**') && part.endsWith('**') ? <strong key={i}>{part.slice(2, -2)}</strong> : <Fragment key={i}>{part}</Fragment>,
  )
}

const onProductPage = (path: string) => /^\/products\/[^/]+$/.test(path)

export default function ChatWidget() {
  const { token, user, ready } = useAuth()
  const { results, showResults, clearResults } = useChatResults()
  const { pathname } = useLocation()
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([greeting()])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [loadingHistory, setLoadingHistory] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Other parts of the site (hero, item page) can open the chat with a suggested question typed in.
  useEffect(() => {
    const onOpen = (e: Event) => {
      const prefill = (e as CustomEvent<{ prefill?: string }>).detail?.prefill
      setOpen(true)
      if (prefill) setInput(prefill)
      window.setTimeout(() => inputRef.current?.focus(), 50)
    }
    window.addEventListener('cc:open-chat', onOpen)
    return () => window.removeEventListener('cc:open-chat', onOpen)
  }, [])

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, busy, open])

  // Logged in: load saved history from the DB. Logged out: start a fresh, unsaved guest chat.
  useEffect(() => {
    if (!ready) return
    if (!user || !token) {
      setMessages([greeting()])
      return
    }
    let cancelled = false
    setLoadingHistory(true)
    fetch('/api/chat/history', { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => (r.ok ? r.json() : { messages: [] }))
      .then((data: { messages: SavedMessage[] }) => {
        if (cancelled) return
        const saved: Message[] = data.messages.map((m) => ({
          role: m.role, content: m.content, products: m.products, resultsTitle: 'From your last chat', saved: true,
        }))
        setMessages([greeting(user.first_name), ...saved])
      })
      .catch(() => { if (!cancelled) setMessages([greeting(user.first_name)]) })
      .finally(() => { if (!cancelled) setLoadingHistory(false) })
    return () => { cancelled = true }
  }, [ready, user?.id, token]) // eslint-disable-line react-hooks/exhaustive-deps

  // Clear on-page chat cards when someone logs out, so the next person doesn't see them.
  const prevUser = useRef(user?.id)
  useEffect(() => {
    if (prevUser.current && !user) clearResults()
    prevUser.current = user?.id
  }, [user, clearResults])

  function pageContext() {
    const match = pathname.match(/^\/products\/([^/]+)$/)
    return {
      path: pathname,
      product_id: match ? decodeURIComponent(match[1]) : null,
      visible_product_ids: results?.products.map((p) => p.product_id) ?? [],
    }
  }

  function send(e: FormEvent) {
    e.preventDefault()
    void sendText(input)
  }

  async function sendText(raw: string) {
    const text = raw.trim()
    if (!text || busy || loadingHistory) return
    // Guests send recent turns from the browser; logged-in history is loaded server-side.
    const history = user
      ? []
      : messages
          .slice(1)
          .filter((m) => !m.error)
          .slice(-HISTORY_TURNS)
          .map(({ role, content, products }) => ({ role, content, product_ids: products?.map((p) => p.product_id) ?? [] }))
    setMessages((m) => [...m, { role: 'user', content: text }])
    setInput('')
    setBusy(true)
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({ message: text, history, page: pageContext() }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Something went wrong. Please try again.')
      const products: ChatProduct[] = data.products ?? []
      const title: string = data.results_title ?? 'Matching items'
      // Skip the on-page row when the only card is the item already on screen.
      const viewingId = pageContext().product_id
      const onlyCurrentItem = products.length === 1 && products[0].product_id === viewingId
      if (products.length > 0 && !onlyCurrentItem) {
        showResults(title, text, products)
        // On phones the panel covers the page, so get out of the way of the new cards.
        if (window.matchMedia('(max-width: 760px)').matches) setOpen(false)
      }
      setMessages((m) => [...m, {
        role: 'assistant', content: data.reply, products, resultsTitle: title,
        degraded: Boolean(data.degraded), retryText: data.degraded ? text : undefined,
      }])
    } catch (err) {
      const msg = err instanceof TypeError ? "Couldn't reach the store. Check your connection." : (err as Error).message
      setMessages((m) => [...m, { role: 'assistant', content: msg, error: true, retryText: text }])
    } finally {
      setBusy(false)
    }
  }

  async function clearHistory() {
    if (!token || !window.confirm('Delete your saved chat history?')) return
    const res = await fetch('/api/chat/history', { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } })
    if (res.ok) setMessages([greeting(user?.first_name)])
  }

  const lastMessage = messages[messages.length - 1]
  const userHasSpoken = messages.some((m) => m.role === 'user' && !m.saved)
  const quickReplies = onProductPage(pathname)
    ? ITEM_REPLIES
    : lastMessage?.role === 'assistant' && lastMessage.products?.length && !lastMessage.saved && !lastMessage.degraded
      ? FOLLOW_UP_REPLIES
      : !userHasSpoken ? STARTER_REPLIES : []

  const firstNewIndex = messages.findIndex((m, i) => i > 0 && !m.saved)
  const hasSaved = messages.some((m) => m.saved)
  const onProduct = onProductPage(pathname)

  return (
    <div className="chat">
      {open && (
        <div className="chat-panel" role="dialog" aria-label="Campus Customs chat">
          <div className="chat-header">
            <div className="chat-id">
              <span className="chat-avatar" aria-hidden>CC</span>
              <div>
                <strong>Campus Customs</strong>
                <small><i className="online" aria-hidden /> Assistant · live stock &amp; prices</small>
              </div>
            </div>
            <div className="chat-header-actions">
              {user && hasSaved && (
                <button className="chat-clear" onClick={clearHistory} title="Delete saved chat history">Clear history</button>
              )}
              <button className="chat-close" onClick={() => setOpen(false)} aria-label="Close chat">×</button>
            </div>
          </div>
          <div className="chat-messages">
            {loadingHistory && <p className="chat-note">Loading your saved chat…</p>}
            {messages.map((m, i) => (
              <Fragment key={i}>
                {i === 1 && m.saved && <p className="chat-note">Saved conversation</p>}
                {i === firstNewIndex && hasSaved && <p className="chat-note">New messages</p>}
                <div className={`chat-turn ${m.role}`}>
                  <div className={`bubble ${m.role}${m.error ? ' error' : ''}${m.degraded ? ' degraded' : ''}`}>{formatText(m.content)}</div>
                  {m.retryText && i === messages.length - 1 && !busy && (
                    <button className="retry-btn" onClick={() => void sendText(m.retryText!)}>↻ Try again</button>
                  )}
                  {m.products && m.products.length > 0 && (
                    <button
                      className="chat-results-chip"
                      onClick={() => showResults(m.resultsTitle ?? 'Matching items', messages[i - 1]?.content ?? '', m.products!)}
                    >
                      <span className="chip-thumbs">
                        {m.products.slice(0, 3).map((p) => <img key={p.product_id} src={p.image_url} alt="" />)}
                      </span>
                      {m.saved
                        ? `Show ${m.products.length === 1 ? 'item' : `${m.products.length} items`} on the page`
                        : m.products.length === 1 ? 'Shown on the page' : `${m.products.length} items shown on the page`}{' '}↑
                    </button>
                  )}
                </div>
              </Fragment>
            ))}
            {busy && <div className="bubble assistant typing" aria-label="Assistant is typing"><span /><span /><span /></div>}
            <div ref={endRef} />
          </div>
          {quickReplies.length > 0 && !loadingHistory && (
            <div className="quick-replies" aria-label="Suggested questions">
              {quickReplies.map((q) => (
                <button key={q} className="quick-reply" disabled={busy} onClick={() => void sendText(q)}>{q}</button>
              ))}
            </div>
          )}
          {!user && <p className="chat-footnote">Guest chat isn't saved. Log in to keep your history.</p>}
          <form className="chat-input" onSubmit={send}>
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={onProduct ? 'Ask about this item…' : 'Ask about merch…'}
              maxLength={1000}
              disabled={busy || loadingHistory}
            />
            <button type="submit" disabled={busy || loadingHistory || !input.trim()} aria-label="Send">
              <svg viewBox="0 0 24 24" aria-hidden><path d="M4 12h14M13 6l6 6-6 6" /></svg>
            </button>
          </form>
        </div>
      )}
      <button className={`chat-toggle${open ? ' open' : ''}`} onClick={() => setOpen((o) => !o)} aria-label={open ? 'Close chat' : 'Open chat'}>
        {open ? (
          <svg viewBox="0 0 24 24" aria-hidden><path d="M6 6l12 12M18 6 6 18" /></svg>
        ) : (
          <>
            <svg viewBox="0 0 24 24" aria-hidden><path d="M4 5h16v11H8l-4 4z" /></svg>
            <span>Ask us</span>
          </>
        )}
      </button>
    </div>
  )
}
