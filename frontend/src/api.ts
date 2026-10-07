export type InventoryRow = { size: string; quantity: number }

export type Product = {
  product_id: string
  name: string
  garment_type: string
  description: string
  short_description: string
  colors: string[]
  search_tags: string[]
  image_url: string
  price: number
  inventory?: InventoryRow[]
  // Stock summary from the list/search endpoints (powers card badges)
  available_sizes?: string[]
  low_stock_sizes?: string[]
  in_stock?: boolean
}

export type SearchResponse = { query: string; corrections: Record<string, string>; products: Product[] }

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(res.status === 404 ? 'Not found' : `Request failed (${res.status})`)
  return res.json() as Promise<T>
}

export const fetchProducts = () => getJson<Product[]>('/api/products')
export const searchProducts = (q: string) => getJson<SearchResponse>(`/api/search?q=${encodeURIComponent(q)}`)
export const fetchProduct = (id: string) => getJson<Product>(`/api/products/${encodeURIComponent(id)}`)

export const formatPrice = (price: number) =>
  price.toLocaleString('en-US', { style: 'currency', currency: 'USD' })

const ALL_SIZES = 6

/** Badge text from live stock, or null when there's nothing worth flagging. */
export function stockBadge(p: { in_stock?: boolean; available_sizes?: string[] }): string | null {
  if (p.in_stock === false || (p.available_sizes && p.available_sizes.length === 0)) return 'Sold out'
  const n = p.available_sizes?.length
  if (n !== undefined && n <= 3 && n < ALL_SIZES) return `Only ${n} size${n === 1 ? '' : 's'} left`
  return null
}

/** Shop categories, matched on garment_type (the DB's labels vary, e.g. "hoodie" vs "hooded sweatshirt"). */
export const CATEGORIES = [
  { slug: 'hoodies', label: 'Hoodies', match: /hood/i },
  { slug: 'crewnecks', label: 'Crewnecks', match: /crewneck|mockneck/i },
  { slug: 'quarter-zips', label: 'Quarter-zips', match: /quarter-zip/i },
  { slug: 'tees', label: 'T-shirts', match: /t-shirt/i },
  { slug: 'outerwear', label: 'Jackets & fleece', match: /jacket/i },
  { slug: 'long-sleeve', label: 'Performance', match: /performance/i },
] as const

export const categoryOf = (p: { garment_type: string }) => CATEGORIES.find((c) => c.match.test(p.garment_type))

/** Ask the chat widget to open (optionally with a suggested message typed in). */
export function openChat(prefill?: string) {
  window.dispatchEvent(new CustomEvent('cc:open-chat', { detail: { prefill } }))
}
