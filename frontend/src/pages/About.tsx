import { Link } from 'react-router-dom'

export default function About() {
  return (
    <>
      <section className="about-hero">
        <p className="eyebrow">About us</p>
        <h1>Made in New Haven, for everyone who calls it home.</h1>
      </section>
      <section className="page narrow prose reveal">
        <p className="drop">
          Campus Customs started with a simple idea: Yale gear should feel as good as the memories it carries.
          From our shop at 57 Broadway, we outfit students, alumni, families, and fans with officially licensed
          apparel, from everyday tees to the hoodie you'll still be wearing at your 25th reunion.
        </p>
        <div className="about-grid">
          <div>
            <h2>What we carry</h2>
            <p>Classic Bulldog designs, residential college crests, varsity sport collections, and graduate school
              pieces. Whether you're repping Davenport, the Divinity School, or the lacrosse team, there's something
              here with your name on it.</p>
          </div>
          <div>
            <h2>How we work</h2>
            <p>We keep it honest. Every price and size you see comes straight from our inventory, and our chat
              assistant uses the same data, so if something's sold out, we'll tell you.</p>
          </div>
        </div>
        <blockquote>“Saturdays at the Bowl, Sundays in the library — always in blue.”</blockquote>
        <h2>Visit us</h2>
        <p>57 Broadway, New Haven, CT 06511. Stop by, try it on, and say hi.</p>
        <Link to="/products" className="btn primary">Browse the shop</Link>
      </section>
    </>
  )
}
