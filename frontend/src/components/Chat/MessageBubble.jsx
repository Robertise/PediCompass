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
      <div className="flex justify-end">
        <div className="message-bubble message-bubble--user" id={`msg-user-${Date.now()}`}>
          {content}
        </div>
      </div>
    )
  }

  // Agent response
  return (
    <div className="flex justify-start w-full">
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
        <div className="alert alert--emergency mb-3">
          <strong>🚨 CALL EMERGENCY SERVICES IMMEDIATELY</strong>
          <p className="mt-2 text-white">
            {response.reason}
          </p>
        </div>
        <div className="bg-bgElevated rounded-md p-4 border-l-[3px] border-emergency">
          <p className="font-semibold mb-2 text-white">
            What to do RIGHT NOW:
          </p>
          <p className="text-gray-200">
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
        <p className="text-gray-200 mb-3">
          To give you the most accurate guidance, I need a little more information:
        </p>
        <div className="flex flex-col gap-2">
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
      <div className="flex flex-col gap-4">

        {/* Urgency badge */}
        {urgency_level && (
          <div>
            <UrgencyBadge level={urgency_level} size="lg" />
          </div>
        )}

        {/* Care pathway summary */}
        {care_pathway && (
          <div className="bg-bgElevated rounded-md p-4">
            <p className="font-semibold text-teal-400 uppercase tracking-wide text-xs mb-2">🏥 Recommended Care</p>
            <p className="text-[1.0625rem] font-semibold text-white mb-2">
              {care_pathway.care_setting}
            </p>

            {care_pathway.immediate_actions?.length > 0 && (
              <>
                <p className="font-semibold text-teal-400 uppercase tracking-wide text-xs mt-3 mb-2">Right now:</p>
                <ul className="pl-5 text-gray-200 list-disc">
                  {care_pathway.immediate_actions.map((action, i) => (
                    <li key={i} className="mb-1">{action}</li>
                  ))}
                </ul>
              </>
            )}

            {care_pathway.clinical_reasoning && (
              <>
                <p className="font-semibold text-teal-400 uppercase tracking-wide text-xs mt-3 mb-2">Why:</p>
                <ReactMarkdown
                  components={{
                    p: ({ children }) => (
                      <p className="text-gray-200 text-[0.9375rem] mb-2">
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
            <p className="font-semibold mb-2 text-white">
              ⚠️ Watch for these warning signs at home:
            </p>
            <ul className="pl-5 text-gray-200 list-disc">
              {warning_signs.map((sign, i) => (
                <li key={i} className="mb-1">{sign}</li>
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
        <p className="text-[0.8125rem] text-gray-400 italic border-t border-white/5 pt-3">
          This guidance is for informational purposes only. Please consult a qualified
          pediatric healthcare professional for proper evaluation and diagnosis.
        </p>
      </div>
    )
  }

  return null
}
