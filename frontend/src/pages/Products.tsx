import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { CATEGORIES, categoryOf, fetchProducts, searchProducts, type Product } from '../api'
import ProductCard from '../components/ProductCard'

type Sort = 'featured' | 'price-asc' | 'price-desc' | 'name'

export default function Products() {
  const [params, setParams] = useSearchParams()
  const cat = params.get('cat') ?? ''
  const [products, setProducts] = useState<Product[] | null>(null)
  const [error, setError] = useState('')
  const [query, setQuery] = useState(params.get('q') ?? '')
  const [hits, setHits] = useState<Product[] | null>(null)
  const [corrections, setCorrections] = useState<Record<string, string>>({})
  const [sort, setSort] = useState<Sort>('featured')
  const [inStockOnly, setInStockOnly] = useState(false)

  useEffect(() => {
    fetchProducts().then(setProducts).catch((e: Error) => setError(e.message))
  }, [])

  // Typo-tolerant search runs on the backend (same ranking as the chat agent), debounced while typing.
  useEffect(() => {
    const q = query.trim()
    if (!q) { setHits(null); setCorrections({}); return }
    let cancelled = false
    const t = setTimeout(() => {
      searchProducts(q)
        .then((r) => { if (!cancelled) { setHits(r.products); setCorrections(r.corrections) } })
        .catch(() => { if (!cancelled) { setHits([]); setCorrections({}) } })
    }, 250)
    return () => { cancelled = true; clearTimeout(t) }
  }, [query])

  const visible = useMemo(() => {
    let list = [...(hits ?? products ?? [])]
    if (cat) list = list.filter((p) => categoryOf(p)?.slug === cat)
    if (inStockOnly) list = list.filter((p) => p.in_stock !== false)
    if (sort === 'price-asc') list.sort((a, b) => a.price - b.price)
    if (sort === 'price-desc') list.sort((a, b) => b.price - a.price)
    if (sort === 'name') list.sort((a, b) => a.name.localeCompare(b.name))
    return list
  }, [hits, products, cat, inStockOnly, sort])

  const counts = useMemo(() => {
    const base = hits ?? products ?? []
    return Object.fromEntries(CATEGORIES.map((c) => [c.slug, base.filter((p) => categoryOf(p)?.slug === c.slug).length]))
  }, [hits, products])

  const setCat = (slug: string) => {
    const next = new URLSearchParams(params)
    if (slug) next.set('cat', slug); else next.delete('cat')
    setParams(next, { replace: true })
  }
  const fixes = Object.entries(corrections)
  const title = CATEGORIES.find((c) => c.slug === cat)?.label ?? 'All products'

  return (
    <section className="page">
      <div className="shop-head">
        <div>
          <p className="eyebrow">Shop</p>
          <h1>{title}</h1>
          {products && <p className="muted">{visible.length} {visible.length === 1 ? 'style' : 'styles'}</p>}
        </div>
        <div className="search-wrap">
          <svg viewBox="0 0 24 24" aria-hidden><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
          <input
            className="search"
            type="search"
            placeholder="Search colleges, sports, colors…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Search products"
          />
        </div>
      </div>

      <div className="toolbar">
        <div className="chips" role="tablist" aria-label="Categories">
          <button role="tab" aria-selected={!cat} className={`chip${!cat ? ' on' : ''}`} onClick={() => setCat('')}>All</button>
          {CATEGORIES.map((c) => (
            <button key={c.slug} role="tab" aria-selected={cat === c.slug} className={`chip${cat === c.slug ? ' on' : ''}`} onClick={() => setCat(c.slug)}>
              {c.label} <span>{counts[c.slug] ?? 0}</span>
            </button>
          ))}
        </div>
        <div className="toolbar-right">
          <label className="toggle">
            <input type="checkbox" checked={inStockOnly} onChange={(e) => setInStockOnly(e.target.checked)} /> In stock
          </label>
          <select value={sort} onChange={(e) => setSort(e.target.value as Sort)} aria-label="Sort">
            <option value="featured">Featured</option>
            <option value="price-asc">Price: low to high</option>
            <option value="price-desc">Price: high to low</option>
            <option value="name">Name A–Z</option>
          </select>
        </div>
      </div>

      {fixes.length > 0 && (
        <p className="search-fix">
          Showing results for <strong>{fixes.map(([, fixed]) => fixed).join(', ')}</strong>
          <span className="muted"> · you typed “{fixes.map(([typed]) => typed).join(', ')}”</span>
        </p>
      )}
      {error && <p className="error">Couldn't load products: {error}</p>}
      {!products && !error && (
        <div className="grid">{Array.from({ length: 8 }, (_, i) => <div key={i} className="card skeleton" />)}</div>
      )}
      {products && visible.length === 0 && (
        <div className="empty">
          <h3>No matches{query ? ` for “${query}”` : ''}</h3>
          <p className="muted">Try a college, a sport, or another category.</p>
        </div>
      )}
      <div className="grid">
        {visible.map((p) => <ProductCard key={p.product_id} product={p} />)}
      </div>
    </section>
  )
}
