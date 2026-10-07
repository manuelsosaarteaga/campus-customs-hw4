import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { categoryOf, fetchProduct, formatPrice, openChat, type Product } from '../api'

export default function ProductDetail() {
  const { productId = '' } = useParams()
  const [product, setProduct] = useState<Product | null>(null)
  const [error, setError] = useState('')
  const [size, setSize] = useState<string | null>(null)

  useEffect(() => {
    setProduct(null)
    setError('')
    setSize(null)
    fetchProduct(productId).then(setProduct).catch((e: Error) => setError(e.message))
  }, [productId])

  if (error) {
    return (
      <section className="page narrow empty">
        <h1>{error === 'Not found' ? 'Product not found' : 'Something went wrong'}</h1>
        <Link to="/products" className="btn primary">Back to the shop</Link>
      </section>
    )
  }
  if (!product) {
    return (
      <section className="page"><div className="detail"><div className="detail-image skeleton" /><div className="detail-info"><div className="skeleton line w60" /><div className="skeleton line w40" /><div className="skeleton line" /></div></div></section>
    )
  }

  const category = categoryOf(product)
  const selected = product.inventory?.find((s) => s.size === size)
  const available = product.inventory?.filter((s) => s.quantity > 0).length ?? 0

  return (
    <section className="page">
      <nav className="crumbs" aria-label="Breadcrumb">
        <Link to="/products">Products</Link>
        {category && <><span>/</span><Link to={`/products?cat=${category.slug}`}>{category.label}</Link></>}
        <span>/</span><span aria-current="page">{product.name}</span>
      </nav>
      <div className="detail">
        <div className="detail-image">
          <img src={product.image_url} alt={product.name} />
        </div>
        <div className="detail-info">
          <p className="eyebrow">{product.garment_type}</p>
          <h1>{product.name}</h1>
          <p className="detail-price">{formatPrice(product.price)}</p>
          <p className="detail-desc">{product.description}</p>

          <div className="detail-block">
            <h3>Colors</h3>
            <p className="muted">{product.colors.join(' · ')}</p>
          </div>

          <div className="detail-block">
            <div className="size-head">
              <h3>Size</h3>
              <span className="muted">{available} of {product.inventory?.length ?? 6} sizes in stock</span>
            </div>
            <div className="sizes" role="radiogroup" aria-label="Sizes">
              {product.inventory?.map((s) => (
                <button
                  key={s.size}
                  role="radio"
                  aria-checked={size === s.size}
                  disabled={s.quantity === 0}
                  className={`size${s.quantity === 0 ? ' out' : ''}${size === s.size ? ' on' : ''}`}
                  onClick={() => setSize(s.size)}
                >
                  <strong>{s.size}</strong>
                  <span>{s.quantity === 0 ? 'Sold out' : s.quantity <= 3 ? `Only ${s.quantity} left` : 'In stock'}</span>
                </button>
              ))}
            </div>
            <p className="size-note" aria-live="polite">
              {selected
                ? selected.quantity <= 3 ? `Size ${selected.size}: only ${selected.quantity} left — available in store at 57 Broadway.` : `Size ${selected.size} is in stock — available in store at 57 Broadway.`
                : 'Select a size to check availability.'}
            </p>
          </div>

          <div className="detail-actions">
            <button className="btn primary" onClick={() => openChat(size ? `Is this available in ${size}?` : 'What colors and sizes does this come in?')}>
              Ask about this item
            </button>
            <Link to={category ? `/products?cat=${category.slug}` : '/products'} className="btn ghost">More {category?.label.toLowerCase() ?? 'styles'}</Link>
          </div>
          <ul className="perks">
            <li>✓ Officially licensed Yale apparel</li>
            <li>✓ Live stock from our New Haven shop</li>
            <li>✓ Questions? Our assistant answers instantly</li>
          </ul>
        </div>
      </div>
    </section>
  )
}
