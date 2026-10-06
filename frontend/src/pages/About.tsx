export default function About() {
  return (
    <section className="section narrow">
      <p className="eyebrow">About us</p>
      <h1>Made for the people who make Yale.</h1>

      <div className="map-wrap">
        <iframe
          title="Map of Campus Customs at 57 Broadway, New Haven, CT 06511"
          src="https://www.google.com/maps?q=57+Broadway,+New+Haven,+CT+06511&z=16&output=embed"
          loading="lazy"
          referrerPolicy="no-referrer-when-downgrade"
          allowFullScreen
        />
      </div>
      <p className="map-caption">
        57 Broadway, New Haven, CT 06511 ·{' '}
        <a
          href="https://www.google.com/maps/search/?api=1&query=57+Broadway%2C+New+Haven%2C+CT+06511"
          target="_blank"
          rel="noreferrer"
        >
          Get directions
        </a>
      </p>
      <p className="lead">
        Campus Customs started with a simple idea: school spirit shouldn’t be scratchy, boxy, or
        boring. We design officially licensed Yale apparel that feels good enough to wear every day.
      </p>

      <h2>Who we dress</h2>
      <p>
        First-years buying their first hoodie. Seniors stocking up before they leave. Parents who
        want everyone at work to know where their kid goes. Alumni who still bleed blue. Whoever you
        are, if you love this place, you’re family here.
      </p>

      <h2>What we stand for</h2>
      <ul className="values">
        <li><strong>Comfort first.</strong> We pick fabrics we’d actually want to wear.</li>
        <li><strong>Honest pride.</strong> Classic marks, team logos, and rivalry designs, all done right.</li>
        <li><strong>Straight answers.</strong> If something’s sold out in your size, we’ll tell you.</li>
      </ul>

      <h2>Come say hi</h2>
      <p>
        We’re at <strong>57 Broadway in New Haven</strong>, a short walk from campus. Can’t make
        it in? We ship to students, families, and alumni around the world.
      </p>
    </section>
  )
}
