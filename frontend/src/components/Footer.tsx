import { Link } from 'react-router-dom'
import { CATEGORIES } from '../api'

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-inner">
        <div className="footer-brand">
          <Link to="/" className="brand light"><span className="brand-mark">CC</span><span className="brand-name">Campus Customs</span></Link>
          <p>Officially licensed Yale apparel, picked by people who live it. Boola Boola.</p>
        </div>
        <div>
          <h4>Shop</h4>
          {CATEGORIES.slice(0, 5).map((c) => <Link key={c.slug} to={`/products?cat=${c.slug}`}>{c.label}</Link>)}
        </div>
        <div>
          <h4>Campus Customs</h4>
          <Link to="/about">Our story</Link>
          <Link to="/signup">Create an account</Link>
          <Link to="/login">Log in</Link>
        </div>
        <div>
          <h4>Visit</h4>
          <p>57 Broadway<br />New Haven, CT 06511</p>
          <p className="muted-light">Custom items are final sale.</p>
        </div>
      </div>
      <div className="footer-base">© {new Date().getFullYear()} Campus Customs · Made in New Haven</div>
    </footer>
  )
}
