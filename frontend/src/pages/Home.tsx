import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { CATEGORIES, categoryOf, fetchProducts, openChat, type Product } from '../api'
import ProductCard from '../components/ProductCard'

const HERO_IDS = ['champion-reverse-weave-hoodie-1', 'davenport-college-crewneck', '2025-yale-vs-harvard-t-shirt']

export default function Home() {
  const [products, setProducts] = useState<Product[]>([])

  useEffect(() => { fetchProducts().then(setProducts).catch(() => setProducts([])) }, [])

  const byId = useMemo(() => new Map(products.map((p) => [p.product_id, p])), [products])
  const hero = HERO_IDS.map((id) => byId.get(id)).filter(Boolean) as Product[]
  const tiles = CATEGORIES.slice(0, 5).map((c) => {
    const items = products.filter((p) => categoryOf(p)?.slug === c.slug)
    return { ...c, count: items.length, image: items.find((p) => p.in_stock !== false)?.image_url }
  })
  const featured = products.filter((p) => /hood|crewneck|quarter-zip/i.test(p.garment_type) && p.in_stock !== false).slice(0, 8)

  return (
    <>
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Fall 2026 · New Haven</p>
          <h1>Wear the Blue.</h1>
          <p className="lede">
            Hoodies, crewnecks, and tees for late nights at Sterling, Saturdays at the Bowl, and every reunion after.
            Officially licensed Yale gear, picked by people who live it.
          </p>
          <div className="hero-actions">
            <Link to="/products" className="btn primary">Shop the collection</Link>
            <button className="btn ghost" onClick={() => openChat('What hoodies do you have?')}>Ask our assistant</button>
          </div>
          <ul className="trust">
            <li><strong>102</strong> styles</li>
            <li><strong>11</strong> college crests</li>
            <li><strong>XS–XXL</strong> live stock</li>
          </ul>
        </div>
        <div className="hero-art" aria-hidden>
          {hero.map((p, i) => (
            <Link key={p.product_id} to={`/products/${p.product_id}`} className={`hero-tile t${i}`} tabIndex={-1}>
              <img src={p.image_url} alt="" />
            </Link>
          ))}
        </div>
      </section>

      <section className="page reveal">
        <div className="section-head">
          <div>
            <p className="eyebrow">Shop by category</p>
            <h2>Find your fit</h2>
          </div>
          <Link to="/products" className="link-arrow">All products →</Link>
        </div>
        <div className="tiles">
          {tiles.map((t) => (
            <Link key={t.slug} to={`/products?cat=${t.slug}`} className="tile">
              {t.image && <img src={t.image} alt="" loading="lazy" />}
              <span className="tile-label">{t.label}<small>{t.count} styles</small></span>
            </Link>
          ))}
        </div>
      </section>

      <section className="pillars reveal">
        <div>
          <span className="pillar-icon" aria-hidden>🏛</span>
          <h3>Your college, your colors</h3>
          <p>From Berkeley to Grace Hopper, find a crest that feels like home.</p>
        </div>
        <div>
          <span className="pillar-icon" aria-hidden>🏈</span>
          <h3>Game-day ready</h3>
          <p>Cheer on the Bulldogs in gear built for cold November afternoons.</p>
        </div>
        <div>
          <span className="pillar-icon" aria-hidden>💬</span>
          <h3>Straight answers</h3>
          <p>Our assistant checks real prices and stock, so you always know what's on the shelf.</p>
        </div>
      </section>

      {featured.length > 0 && (
        <section className="page reveal">
          <div className="section-head">
            <div>
              <p className="eyebrow">Layer up</p>
              <h2>Sweatshirt season</h2>
            </div>
            <Link to="/products?cat=hoodies" className="link-arrow">Shop hoodies →</Link>
          </div>
          <div className="grid">
            {featured.map((p) => <ProductCard key={p.product_id} product={p} />)}
          </div>
        </section>
      )}

      <section className="cta-band reveal">
        <div>
          <h2>Not sure what to get?</h2>
          <p>Tell our assistant what you're after — a college, a sport, a budget — and the right picks appear on the page.</p>
        </div>
        <button className="btn light" onClick={() => openChat('Gifts under $40')}>Start a chat</button>
      </section>
    </>
  )
}
