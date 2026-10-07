import { Link } from 'react-router-dom'
import { categoryOf, formatPrice, stockBadge } from '../api'

type CardProduct = {
  product_id: string
  name: string
  price: number
  image_url: string
  short_description: string
  garment_type?: string
  colors?: string[]
  in_stock?: boolean
  available_sizes?: string[]
}

const SWATCH: Record<string, string> = {
  navy: '#1f2a44', blue: '#286dc0', white: '#ffffff', gray: '#9aa0a6', grey: '#9aa0a6', black: '#1d1d1f',
  red: '#b3261e', yellow: '#f2c230', green: '#2e7d32', charcoal: '#3c4043', heather: '#b8bcc2', cream: '#f3ead7',
  maroon: '#6d1a2a', pink: '#f4a6c0', orange: '#e8710a', purple: '#6a3fa0', brown: '#6d4c41', silver: '#c0c4c8',
}
function swatchColor(name: string) {
  const n = name.toLowerCase()
  const key = Object.keys(SWATCH).find((k) => n.includes(k))
  return key ? SWATCH[key] : '#d0d4d9'
}

export default function ProductCard({ product, current = false }: { product: CardProduct; current?: boolean }) {
  const badge = stockBadge(product)
  const category = product.garment_type ? categoryOf({ garment_type: product.garment_type })?.label : undefined
  return (
    <Link
      to={`/products/${product.product_id}`}
      className={`card${current ? ' current' : ''}`}
      aria-current={current ? 'page' : undefined}
    >
      <div className="card-image">
        <img src={product.image_url} alt={product.name} loading="lazy" />
        {badge && <span className={`badge${badge === 'Sold out' ? '' : ' low'}`}>{badge}</span>}
        <span className="card-cta" aria-hidden>View details →</span>
      </div>
      <div className="card-body">
        {category && <p className="card-eyebrow">{category}</p>}
        <h3>{product.name}</h3>
        <p className="card-desc">{product.short_description}</p>
        <div className="card-foot">
          <p className="price">{formatPrice(product.price)}</p>
          {product.colors && product.colors.length > 0 && (
            <span className="swatches" aria-label={`Colors: ${product.colors.join(', ')}`}>
              {product.colors.slice(0, 4).map((c) => <i key={c} style={{ background: swatchColor(c) }} title={c} />)}
            </span>
          )}
        </div>
      </div>
    </Link>
  )
}
