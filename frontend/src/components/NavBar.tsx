import { useEffect, useState } from 'react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

export default function NavBar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const [scrolled, setScrolled] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])
  useEffect(() => setMenuOpen(false), [pathname])

  return (
    <>
      <div className="announce">
        <span>Officially licensed Yale apparel</span>
        <span className="dot" aria-hidden>•</span>
        <span>Visit us at 57 Broadway, New Haven</span>
        <span className="dot hide-sm" aria-hidden>•</span>
        <span className="hide-sm">Ask our assistant about any size, any time</span>
      </div>
      <header className={`nav${scrolled ? ' scrolled' : ''}`}>
        <div className="nav-inner">
          <Link to="/" className="brand" aria-label="Campus Customs home">
            <span className="brand-mark">CC</span>
            <span className="brand-name">Campus Customs</span>
          </Link>
          <button className="menu-btn" aria-label="Menu" aria-expanded={menuOpen} onClick={() => setMenuOpen((o) => !o)}>
            <span /><span />
          </button>
          <nav className={`nav-links${menuOpen ? ' open' : ''}`}>
            <NavLink to="/" end>Home</NavLink>
            <NavLink to="/products">Products</NavLink>
            <NavLink to="/about">About Us</NavLink>
            {user ? (
              <>
                <span className="nav-user">Hi, {user.first_name}</span>
                <button className="nav-link-btn" onClick={() => { logout(); navigate('/') }}>Log out</button>
              </>
            ) : (
              <>
                <NavLink to="/login">Log in</NavLink>
                <NavLink to="/signup" className="nav-cta">Create account</NavLink>
              </>
            )}
          </nav>
        </div>
      </header>
    </>
  )
}
