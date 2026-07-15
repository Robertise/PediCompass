const STARTERS = [
  {
    label: "Ask about my child's symptoms",
    message: "I'd like to ask about my child's symptoms.",
    description: "Get age-appropriate care guidance",
  },
  {
    label: "Learn about children's health",
    message: "I have a general question about children's health.",
    description: "Explore the pediatric health topics",
  },
]

export default function ConversationStarter({ onSelect }) {
  return (
    <div className="flex flex-col sm:flex-row gap-md w-full mt-xs">
      {STARTERS.map((starter, i) => (
        <button
          key={i}
          onClick={() => onSelect(starter.message)}
          className="flex-1 flex flex-col items-start gap-xs bg-surface-container hover:bg-surface-container-high rounded-2xl px-md py-sm text-left transition-all hover:shadow-sm hover:-translate-y-[1px] active:translate-y-0"
        >
          <div className="flex items-center gap-sm">
            <span className="text-label-md font-label-md text-on-surface">
              {starter.label}
            </span>
          </div>
          <span className="text-body-sm font-body-sm text-on-surface-variant">
            {starter.description}
          </span>
        </button>
      ))}
    </div>
  )
}
