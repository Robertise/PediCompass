import { Link } from 'react-router-dom'

export default function HomePage() {
  return (
    <div className="page" style={{ padding: 0 }}>
      <section className="hero text-center py-12 px-4 bg-[radial-gradient(ellipse_at_top,_rgba(0,180,216,0.1)_0%,_transparent_60%),_var(--color-bg-deep)]">
        <div className="container max-w-7xl mx-auto">
          <span className="hero-badge">Evidence-Based Pediatric Triage</span>
          <h1 className="hero-title text-4xl md:text-6xl font-extrabold leading-tight mb-6">
            Navigate your child's health with <span className="text-teal-400">confidence.</span>
          </h1>
          <p className="text-xl max-w-2xl mx-auto mb-8 text-gray-200">
            PediCompass provides immediate, age-stratified symptom analysis backed by WHO, NICE, and AAP guidelines.
          </p>
          <div className="flex justify-center gap-4">
            <Link to="/chat" className="btn btn-primary btn-lg">Start Assessment</Link>
            <Link to="/auth" className="btn btn-secondary btn-lg">Create Profile</Link>
          </div>

          <div className="feature-grid">
            <div className="feature-card">
              <div className="feature-icon">🛡️</div>
              <h3 className="mb-2">Safety First</h3>
              <p>Immediate detection of pediatric emergency red flags with deterministic safety screens.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">👶</div>
              <h3 className="mb-2">Age-Stratified</h3>
              <p>Because a fever in a 2-week-old is entirely different from a fever in a 3-year-old.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">📚</div>
              <h3 className="mb-2">Clinical Guidelines</h3>
              <p>Recommendations are grounded in retrieved snippets from official clinical guidelines.</p>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
