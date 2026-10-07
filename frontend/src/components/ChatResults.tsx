import { useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import { useChatResults } from '../chatResults'
import ProductCard from './ProductCard'

/** On-page product cards for the latest chat search. Rendered above every page. */
export default function ChatResults() {
  const { results, clearResults } = useChatResults()
  const { pathname } = useLocation()
  const ref = useRef<HTMLElement>(null)

  // New results: bring them into view and replay the entrance animation.
  useEffect(() => {
    if (!results || !ref.current) return
    ref.current.classList.remove('fresh')
    void ref.current.offsetWidth
    ref.current.classList.add('fresh')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [results?.id])

  if (!results || results.products.length === 0) return null
  const currentId = pathname.startsWith('/products/') ? decodeURIComponent(pathname.split('/')[2] ?? '') : ''

  return (
    <section ref={ref} id="chat-results" className="chat-results" aria-label="Products from your chat">
      <div className="chat-results-head">
        <div>
          <p className="eyebrow">From your chat</p>
          <h2>{results.title} <span className="muted count">{results.products.length}</span></h2>
          {results.query && <p className="muted small-q">“{results.query}”</p>}
        </div>
        <button className="btn ghost small" onClick={clearResults}>Clear</button>
      </div>
      <div className="chat-results-row">
        {results.products.map((p) => (
          <ProductCard key={p.product_id} product={p} current={p.product_id === currentId} />
        ))}
      </div>
    </section>
  )
}
