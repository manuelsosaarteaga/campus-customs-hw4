import { useEffect } from 'react'
import { Route, Routes, useLocation } from 'react-router-dom'
import { useReveal } from './motion'
import NavBar from './components/NavBar'
import Footer from './components/Footer'
import ChatWidget from './components/ChatWidget'
import ChatResults from './components/ChatResults'
import Home from './pages/Home'
import Products from './pages/Products'
import ProductDetail from './pages/ProductDetail'
import About from './pages/About'
import Login from './pages/Login'
import Signup from './pages/Signup'

export default function App() {
  const { pathname } = useLocation()
  useReveal(pathname)
  useEffect(() => { window.scrollTo({ top: 0 }) }, [pathname])
  return (
    <div className="app">
      <NavBar />
      <main>
        <ChatResults />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/products" element={<Products />} />
          <Route path="/products/:productId" element={<ProductDetail />} />
          <Route path="/about" element={<About />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="*" element={<section className="page narrow"><h1>Page not found</h1></section>} />
        </Routes>
      </main>
      <Footer />
      <ChatWidget />
    </div>
  )
}
