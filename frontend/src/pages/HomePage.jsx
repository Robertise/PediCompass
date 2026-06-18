import { Link } from 'react-router-dom'

export default function HomePage() {
  return (
    <div className="page" style={{ padding: 0 }}>
      <section className="hero">
        <div className="container">
          <span className="hero-badge">Evidence-Based Pediatric Triage</span>
          <h1 className="hero-title">
            Navigate your child's health with <span>confidence.</span>
          </h1>
          <p style={{ fontSize: '1.25rem', maxWidth: '600px', margin: '0 auto var(--space-8)' }}>
            PediCompass provides immediate, age-stratified symptom analysis backed by WHO, NICE, and AAP guidelines.
          </p>
          <div className="flex justify-center gap-4">
            <Link to="/chat" className="btn btn-primary btn-lg">Start Assessment</Link>
            <Link to="/auth" className="btn btn-secondary btn-lg">Create Profile</Link>
          </div>

          <div className="feature-grid">
            <div className="feature-card">
              <div className="feature-icon">🛡️</div>
              <h3 style={{ marginBottom: '8px' }}>Safety First</h3>
              <p>Immediate detection of pediatric emergency red flags with deterministic safety screens.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">👶</div>
              <h3 style={{ marginBottom: '8px' }}>Age-Stratified</h3>
              <p>Because a fever in a 2-week-old is entirely different from a fever in a 3-year-old.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">📚</div>
              <h3 style={{ marginBottom: '8px' }}>Clinical Guidelines</h3>
              <p>Recommendations are grounded in retrieved snippets from official clinical guidelines.</p>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
