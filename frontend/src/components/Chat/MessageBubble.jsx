import ReactMarkdown from 'react-markdown'
import UrgencyBadge from './UrgencyBadge'
import CitedSources from './CitedSources'
import PreVisitChecklist from './PreVisitChecklist'

export default function MessageBubble({ role, content }) {
  if (role === 'user') {
    return (
      <div className="flex items-start gap-sm justify-end max-w-3xl mx-auto w-full">
        <div className="bg-primary-container/10 text-on-surface p-md rounded-2xl rounded-tr-sm shadow-[0_4px_24px_rgba(0,80,203,0.04)] text-body-md font-body-md whitespace-pre-wrap">
          {content}
        </div>
        <div className="w-10 h-10 rounded-full bg-surface-container flex items-center justify-center shrink-0">
          <span className="material-symbols-outlined text-primary">person</span>
        </div>
      </div>
    )
  }

  // Agent response
  return (
    <div className="flex items-start gap-sm max-w-3xl mx-auto w-full">
      <div className="w-10 h-10 rounded-full bg-primary-container/20 flex items-center justify-center shrink-0">
        <span className="material-symbols-outlined text-primary">smart_toy</span>
      </div>
      <div className="flex flex-col gap-sm w-full">
        <AgentResponseCard response={content} />
      </div>
    </div>
  )
}

function AgentResponseCard({ response }) {
  if (!response) return null

  // ── Error response ────────────────────────────────────────────────────────
  if (response.type === 'error') {
    return (
      <div className="bg-error-container/20 text-on-surface p-md rounded-2xl rounded-tl-sm border border-error-container/50 text-body-md font-body-md">
        <p className="text-error font-bold mb-1 flex items-center gap-1">
          <span className="material-symbols-outlined text-[18px]">error</span> Error
        </p>
        <p>{response.reason || 'An unexpected error occurred.'}</p>
      </div>
    )
  }

  // ── Emergency response ────────────────────────────────────────────────────
  if (response.type === 'emergency') {
    return (
      <div className="bg-surface border border-error-container/50 rounded-[20px] p-md shadow-[0_8px_32px_rgba(0,0,0,0.04)] overflow-hidden flex flex-col gap-md w-full">
        <div className="flex flex-col md:flex-row gap-sm bg-error/10 p-sm rounded-xl border border-error/20">
          <div className="bg-error text-on-error flex flex-col items-center justify-center p-sm rounded-lg min-w-[120px]">
            <span className="material-symbols-outlined text-[32px] mb-xs">warning</span>
            <span className="text-label-md font-label-md font-bold uppercase tracking-wider text-center">EMERGENCY</span>
          </div>
          <div className="flex flex-col justify-center">
            <span className="text-headline-sm font-headline-sm text-error">Call Emergency Services Now</span>
            <span className="text-body-sm font-body-sm text-on-surface-variant mt-1">{response.reason}</span>
          </div>
        </div>
        
        {response.care_pathway?.immediate_actions?.length > 0 && (
          <div className="flex flex-col gap-sm mt-xs">
            <span className="text-label-md font-label-md text-error">What to do RIGHT NOW:</span>
            <ul className="space-y-sm">
              {response.care_pathway.immediate_actions.map((action, i) => (
                <li key={i} className="flex items-start gap-sm text-body-md font-body-md text-on-surface">
                  <span className="material-symbols-outlined text-error text-[20px] shrink-0">priority_high</span>
                  <span>{action}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    )
  }

  // ── Clarification request ─────────────────────────────────────────────────
  if (response.type === 'clarification') {
    return (
      <>
        <div className="bg-surface-container-low text-on-surface p-md rounded-2xl rounded-tl-sm shadow-[0_2px_12px_rgba(0,0,0,0.02)] text-body-md font-body-md">
          <p>To better understand the situation, I need to ask a few more questions:</p>
        </div>
        {response.clarification_questions?.length > 0 && (
          <div className="flex flex-col gap-xs mt-1">
            {response.clarification_questions.map((q, i) => (
              <div key={i} className="bg-surface border border-outline-variant/30 px-sm py-sm rounded-xl text-body-md font-body-md text-on-surface flex items-start gap-2 shadow-sm">
                <span className="material-symbols-outlined text-primary text-[20px] shrink-0">help</span>
                <span>{q}</span>
              </div>
            ))}
          </div>
        )}
      </>
    )
  }

  // ── Full recommendation ───────────────────────────────────────────────────
  if (response.type === 'recommendation') {
    const { urgency_level, care_pathway, pre_visit_checklist, warning_signs, cited_sources } = response

    return (
      <>
        <div className="bg-surface-container-low text-on-surface p-md rounded-2xl rounded-tl-sm shadow-[0_2px_12px_rgba(0,0,0,0.02)] text-body-md font-body-md mb-xs">
          <p>Based on the information provided, here is the care pathway recommendation.</p>
        </div>

        <div className="bg-surface border border-outline-variant/40 rounded-[20px] p-md shadow-[0_8px_32px_rgba(0,0,0,0.04)] overflow-hidden flex flex-col gap-md">
          {/* Urgency Badge (Inline redesign) */}
          {urgency_level && (
            <UrgencyBadge level={urgency_level} />
          )}

          {/* Care Pathway */}
          {care_pathway && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-sm">
              <div className="flex gap-sm p-sm bg-surface-container-lowest rounded-xl border border-outline-variant/20">
                <span className="material-symbols-outlined text-primary text-[28px]">local_hospital</span>
                <div className="flex flex-col">
                  <span className="text-label-sm font-label-sm text-on-surface-variant mb-[2px]">Recommended Care Setting</span>
                  <span className="text-label-md font-label-md text-on-surface">{care_pathway.care_setting}</span>
                </div>
              </div>
              <div className="flex gap-sm p-sm bg-surface-container-lowest rounded-xl border border-outline-variant/20">
                <span className="material-symbols-outlined text-tertiary text-[28px]">schedule</span>
                <div className="flex flex-col">
                  <span className="text-label-sm font-label-sm text-on-surface-variant mb-[2px]">Timeframe</span>
                  <span className="text-label-md font-label-md text-on-surface">As guided by setting</span>
                </div>
              </div>
            </div>
          )}

          {care_pathway?.clinical_reasoning && (
             <div className="text-body-sm text-on-surface-variant">
                <ReactMarkdown>{care_pathway.clinical_reasoning}</ReactMarkdown>
             </div>
          )}

          <hr className="border-outline-variant/20" />

          {/* Actions & Warnings */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-md">
            {care_pathway?.immediate_actions?.length > 0 && (
              <div className="flex flex-col gap-sm">
                <span className="text-label-md font-label-md text-on-surface">What You Can Do Now:</span>
                <ul className="space-y-sm">
                  {care_pathway.immediate_actions.map((action, i) => (
                    <li key={i} className="flex items-start gap-sm text-body-sm font-body-sm text-on-surface-variant">
                      <span className="material-symbols-outlined text-primary text-[20px] shrink-0">check_circle</span>
                      <span>{action}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {warning_signs?.length > 0 && (
              <div className="flex flex-col gap-sm bg-error-container/10 p-sm rounded-xl border border-error-container/30">
                <span className="text-label-md font-label-md text-error">Warning Signs - Seek Care Immediately:</span>
                <ul className="space-y-[4px]">
                  {warning_signs.map((sign, i) => (
                    <li key={i} className="flex items-center gap-xs text-body-sm font-body-sm text-on-surface-variant">
                      <span className="w-1.5 h-1.5 rounded-full bg-error shrink-0"></span> {sign}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          <PreVisitChecklist items={pre_visit_checklist} />
          
          <CitedSources sources={cited_sources} />

          <div className="bg-surface-container-low p-sm rounded-lg text-label-sm font-label-sm text-on-surface-variant text-center mt-2">
            This is not a medical diagnosis. Trust your instincts and seek medical help if concerned.
          </div>
        </div>
      </>
    )
  }

  // Fallback for simple text messages (though agent usually sends JSON)
  return (
    <div className="bg-surface-container-low text-on-surface p-md rounded-2xl rounded-tl-sm shadow-[0_2px_12px_rgba(0,0,0,0.02)] text-body-md font-body-md whitespace-pre-wrap">
      {typeof response === 'string' ? response : JSON.stringify(response)}
    </div>
  )
}
