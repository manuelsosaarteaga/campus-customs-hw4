import { createContext, useCallback, useContext, useState, type ReactNode } from 'react'

/** A product card sent by POST /api/chat (built from the DB on the backend). */
export type ChatProduct = {
  product_id: string
  name: string
  garment_type: string
  price: number
  price_display: string
  image_url: string
  short_description: string
  colors: string[]
  in_stock: boolean
  available_sizes: string[]
}

export type ChatResults = { id: number; title: string; query: string; products: ChatProduct[] }

type ChatResultsValue = {
  results: ChatResults | null
  showResults: (title: string, query: string, products: ChatProduct[]) => void
  clearResults: () => void
}

const STORAGE_KEY = 'cc_chat_results'
const ChatResultsContext = createContext<ChatResultsValue | null>(null)

function readStored(): ChatResults | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as ChatResults) : null
  } catch {
    return null
  }
}

function store(results: ChatResults | null) {
  try {
    results ? sessionStorage.setItem(STORAGE_KEY, JSON.stringify(results)) : sessionStorage.removeItem(STORAGE_KEY)
  } catch { /* ignore */ }
}

/** Holds the latest chat search results so any page can render them as cards. */
export function ChatResultsProvider({ children }: { children: ReactNode }) {
  const [results, setResults] = useState<ChatResults | null>(readStored)

  const showResults = useCallback((title: string, query: string, products: ChatProduct[]) => {
    const next = { id: Date.now(), title, query, products }
    store(next)
    setResults(next)
  }, [])

  const clearResults = useCallback(() => { store(null); setResults(null) }, [])

  return (
    <ChatResultsContext.Provider value={{ results, showResults, clearResults }}>{children}</ChatResultsContext.Provider>
  )
}

export function useChatResults() {
  const ctx = useContext(ChatResultsContext)
  if (!ctx) throw new Error('useChatResults must be used inside ChatResultsProvider')
  return ctx
}
