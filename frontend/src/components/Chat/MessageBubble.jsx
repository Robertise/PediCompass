import ReactMarkdown from 'react-markdown'
import UrgencyBadge from './UrgencyBadge'
import CitedSources from './CitedSources'
import PreVisitChecklist from './PreVisitChecklist'

const MARKDOWN_STYLES = "space-y-3 [&>ul]:list-disc [&>ul]:ml-6 [&>ul>li]:pl-1 [&>ul>li]:mt-1 [&>ol]:list-decimal [&>ol]:ml-6 [&>ol>li]:pl-1 [&>ol>li]:mt-1 [&>p]:leading-relaxed"

/**
 * MessageBubble — renders a single conversation turn.
 *
 * Design: ChatGPT/Claude style — no user/AI avatar icons.
 *   • User messages: bubble aligned right, surface-container background
 *   • AI messages:   text rendered directly on page background (no floating bubble)
 */
export default function MessageBubble({ role, content, onQuickReply }) {
  if (role === 'user') {
    return (
      <div className="flex justify-end max-w-[52rem] mx-auto w-full">
        <div className="bg-surface-container text-on-surface px-md py-sm rounded-2xl rounded-tr-[4px] text-body-md font-body-md whitespace-pre-wrap max-w-[85%] md:max-w-[75%] shadow-sm">
          {content}
        </div>
      </div>
    )
  }

  // Agent response — rendered directly on page, no bubble wrapper or icon
  return (
    <div className="max-w-[52rem] mx-auto w-full">
      <AgentResponseCard response={content} onQuickReply={onQuickReply} />
    </div>
  )
}

function AgentResponseCard({ response, onQuickReply }) {
  if (!response) return null

  // ── Greeting response ──────────────────────────────────────────────────────
  if (response.type === 'greeting') {
    return (
      <div className={`text-body-md font-body-md text-on-surface ${MARKDOWN_STYLES}`}>
        <ReactMarkdown>{response.parent_message}</ReactMarkdown>
      </div>
    )
  }

  // ── General response ───────────────────────────────────────────────────────
  if (response.type === 'general') {
    return (
      <div className="flex flex-col gap-md">
        <div className="flex items-center gap-xs text-on-surface-variant">
          <span className="material-symbols-outlined text-[16px]">menu_book</span>
          <span className="text-label-sm font-label-sm uppercase tracking-wider">General Knowledge</span>
        </div>
        <div className={`text-body-md font-body-md text-on-surface ${MARKDOWN_STYLES}`}>
          <ReactMarkdown>{response.parent_message}</ReactMarkdown>
        </div>
        {response.cited_sources?.length > 0 && (
          <CitedSources sources={response.cited_sources} />
        )}
        <div className="text-label-sm font-label-sm text-on-surface-variant text-center mt-1">
          General health information only. Not a substitute for professional medical advice.
        </div>
      </div>
    )
  }

  // ── Confirmation response ──────────────────────────────────────────────────
  if (response.type === 'confirmation') {
    return (
      <div className="flex flex-col gap-sm">
        <p className="text-body-md font-body-md text-on-surface">
          {response.parent_message}
        </p>
        {response.confirmation_options?.map((option, i) => (
          <button
            key={i}
            onClick={() => onQuickReply?.(option)}
            className="w-full text-left bg-surface-container hover:bg-surface-container-high
                       border border-outline/20 rounded-xl px-md py-sm text-body-md
                       font-body-md text-on-surface transition-colors cursor-pointer"
          >
            {option}
          </button>
        ))}
      </div>
    )
  }

  // ── Error response ─────────────────────────────────────────────────────────
  if (response.type === 'error') {
    return (
      <div className="bg-error-container/15 text-on-surface px-md py-sm rounded-xl border border-error/20 text-body-md font-body-md">
        <p className="text-error font-semibold mb-1 flex items-center gap-1">
          <span className="material-symbols-outlined text-[18px]">error_outline</span>
          Something went wrong
        </p>
        <p className="text-on-surface-variant">{response.reason || 'An unexpected error occurred.'}</p>
      </div>
    )
  }

  // ── Emergency response ─────────────────────────────────────────────────────
  if (response.type === 'emergency') {
    return (
      <div className="bg-surface border border-error/30 rounded-[20px] p-md shadow-[0_8px_32px_rgba(0,0,0,0.06)] flex flex-col gap-md w-full">
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

  // ── Clarification request ──────────────────────────────────────────────────
  if (response.type === 'clarification') {
    return (
      <div className="flex flex-col gap-sm">
        <p className="text-body-md font-body-md text-on-surface">
          To better understand the situation, I need a bit more information:
        </p>
        {response.clarification_questions?.length > 0 && (
          <div className="flex flex-col gap-sm">
            {response.clarification_questions.map((q, i) => (
              <div
                key={i}
                className="bg-surface-container shadow-sm px-sm py-sm rounded-xl text-body-md font-body-md text-on-surface flex items-start gap-2"
              >
                <span className="material-symbols-outlined text-primary text-[18px] shrink-0 mt-[2px]">help_outline</span>
                <span>{q}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }

  // ── Full recommendation ────────────────────────────────────────────────────
  if (response.type === 'recommendation') {
    const { urgency_level, care_pathway, pre_visit_checklist, warning_signs, cited_sources } = response

    return (
      <div className="flex flex-col gap-md">
        <div className="bg-transparent p-1 overflow-hidden flex flex-col gap-md">
          {/* Urgency Badge */}
          {urgency_level && <UrgencyBadge level={urgency_level} />}

          {/* Care Pathway cards */}
          {care_pathway && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-sm">
              <div className="flex gap-sm p-sm bg-surface-container-low rounded-xl">
                <span className="material-symbols-outlined text-primary text-[28px]">local_hospital</span>
                <div className="flex flex-col">
                  <span className="text-label-sm font-label-sm text-on-surface-variant mb-[2px]">Recommended Care Setting</span>
                  <span className="text-label-md font-label-md text-on-surface">{care_pathway.care_setting}</span>
                </div>
              </div>
              <div className="flex gap-sm p-sm bg-surface-container-low rounded-xl">
                <span className="material-symbols-outlined text-tertiary text-[28px]">schedule</span>
                <div className="flex flex-col">
                  <span className="text-label-sm font-label-sm text-on-surface-variant mb-[2px]">Timeframe</span>
                  <span className="text-label-md font-label-md text-on-surface">As guided by setting</span>
                </div>
              </div>
            </div>
          )}

          {/* Clinical reasoning prose */}
          {care_pathway?.clinical_reasoning && (
            <div className={`text-body-sm text-on-surface-variant ${MARKDOWN_STYLES}`}>
              <ReactMarkdown>{care_pathway.clinical_reasoning}</ReactMarkdown>
            </div>
          )}

          <div className="w-full h-px bg-black/10 dark:bg-white/15 my-xs" />

          {/* Actions & Warnings */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-md">
            {care_pathway?.immediate_actions?.length > 0 && (
              <div className="flex flex-col gap-sm bg-[#0ea5e9]/10 p-sm rounded-xl border-none">
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
              <div className="flex flex-col gap-sm bg-[#ef4444]/10 p-sm rounded-xl border-none">
                <span className="text-label-md font-label-md text-error">Warning Signs — Seek Care Immediately:</span>
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

          <div className="bg-transparent p-sm text-label-sm font-label-sm text-on-surface-variant text-center mt-2">
            This is not a medical diagnosis. Trust your instincts and seek medical help if concerned.
          </div>
        </div>
      </div>
    )
  }

  // Fallback for plain text
  return (
    <div className="text-body-md font-body-md text-on-surface whitespace-pre-wrap">
      {typeof response === 'string' ? response : JSON.stringify(response)}
    </div>
  )
}
