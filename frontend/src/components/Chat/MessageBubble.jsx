import ReactMarkdown from 'react-markdown'
import UrgencyBadge from './UrgencyBadge'
import ReasoningTrace from './ReasoningTrace'
import CitedSources from './CitedSources'
import PreVisitChecklist from './PreVisitChecklist'

/**
 * MessageBubble — renders a single chat turn.
 *
 * User messages: simple bubble on the right.
 * Agent responses: rich card on the left with urgency badge, care pathway,
 *                  checklist, warning signs, sources, and reasoning trace.
 *
 * @param {Object} props
 * @param {'user'|'agent'} props.role
 * @param {string|Object}  props.content  - string for user, AgentResponse object for agent
 */
export default function MessageBubble({ role, content }) {
  if (role === 'user') {
    return (
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <div className="message-bubble message-bubble--user" id={`msg-user-${Date.now()}`}>
          {content}
        </div>
      </div>
    )
  }

  // Agent response
  return (
    <div style={{ display: 'flex', justifyContent: 'flex-start', width: '100%' }}>
      <div className="message-bubble message-bubble--agent">
        <AgentResponseCard response={content} />
      </div>
    </div>
  )
}

function AgentResponseCard({ response }) {
  if (!response) return null

  // ── Emergency response ────────────────────────────────────────────────────
  if (response.type === 'emergency') {
    return (
      <div>
        <div className="alert alert--emergency" style={{ marginBottom: '12px' }}>
          <strong>🚨 CALL EMERGENCY SERVICES IMMEDIATELY</strong>
          <p style={{ marginTop: '8px', color: 'var(--color-white)' }}>
            {response.reason}
          </p>
        </div>
        <div style={{
          background: 'var(--color-bg-elevated)',
          borderRadius: 'var(--radius-md)',
          padding: '16px',
          borderLeft: '3px solid var(--urgency-emergency)',
        }}>
          <p style={{ fontWeight: 600, marginBottom: '8px', color: 'var(--color-white)' }}>
            What to do RIGHT NOW:
          </p>
          <p style={{ color: 'var(--color-gray-200)' }}>
            {response.care_pathway?.immediate_actions?.[0] || 'Call 999 / 911 / your local emergency number immediately.'}
          </p>
        </div>
        {response.reasoning_trace && <ReasoningTrace trace={response.reasoning_trace} />}
      </div>
    )
  }

  // ── Clarification request ─────────────────────────────────────────────────
  if (response.type === 'clarification') {
    return (
      <div>
        <p style={{ color: 'var(--color-gray-200)', marginBottom: '12px' }}>
          To give you the most accurate guidance, I need a little more information:
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {response.clarification_questions?.map((q, i) => (
            <div key={i} className="alert alert--info">
              {q}
            </div>
          ))}
        </div>
      </div>
    )
  }

  // ── Full recommendation ───────────────────────────────────────────────────
  if (response.type === 'recommendation') {
    const { urgency_level, care_pathway, pre_visit_checklist, warning_signs, cited_sources, reasoning_trace } = response

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

        {/* Urgency badge */}
        {urgency_level && (
          <div>
            <UrgencyBadge level={urgency_level} size="lg" />
          </div>
        )}

        {/* Care pathway summary */}
        {care_pathway && (
          <div style={{
            background: 'var(--color-bg-elevated)',
            borderRadius: 'var(--radius-md)',
            padding: '16px',
          }}>
            <p className="section-heading">🏥 Recommended Care</p>
            <p style={{
              fontSize: '1.0625rem',
              fontWeight: 600,
              color: 'var(--color-white)',
              marginBottom: '8px',
            }}>
              {care_pathway.care_setting}
            </p>

            {care_pathway.immediate_actions?.length > 0 && (
              <>
                <p className="section-heading" style={{ marginTop: '12px' }}>Right now:</p>
                <ul style={{ paddingLeft: '20px', color: 'var(--color-gray-200)' }}>
                  {care_pathway.immediate_actions.map((action, i) => (
                    <li key={i} style={{ marginBottom: '4px' }}>{action}</li>
                  ))}
                </ul>
              </>
            )}

            {care_pathway.clinical_reasoning && (
              <>
                <p className="section-heading" style={{ marginTop: '12px' }}>Why:</p>
                <ReactMarkdown
                  components={{
                    p: ({ children }) => (
                      <p style={{ color: 'var(--color-gray-200)', fontSize: '0.9375rem' }}>
                        {children}
                      </p>
                    ),
                  }}
                >
                  {care_pathway.clinical_reasoning}
                </ReactMarkdown>
              </>
            )}
          </div>
        )}

        {/* Warning signs */}
        {warning_signs?.length > 0 && (
          <div className="alert alert--warning">
            <p style={{ fontWeight: 600, marginBottom: '8px', color: 'var(--color-white)' }}>
              ⚠️ Watch for these warning signs at home:
            </p>
            <ul style={{ paddingLeft: '20px', color: 'var(--color-gray-200)' }}>
              {warning_signs.map((sign, i) => (
                <li key={i} style={{ marginBottom: '4px' }}>{sign}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Pre-visit checklist */}
        <PreVisitChecklist items={pre_visit_checklist} />

        {/* Sources */}
        <CitedSources sources={cited_sources} />

        {/* Reasoning trace */}
        <ReasoningTrace trace={reasoning_trace} />

        {/* Disclaimer */}
        <p style={{
          fontSize: '0.8125rem',
          color: 'var(--color-gray-400)',
          fontStyle: 'italic',
          borderTop: '1px solid rgba(255,255,255,0.05)',
          paddingTop: '12px',
        }}>
          This guidance is for informational purposes only. Please consult a qualified
          pediatric healthcare professional for proper evaluation and diagnosis.
        </p>
      </div>
    )
  }

  return null
}
