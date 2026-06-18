const URGENCY_CONFIG = {
  emergency: { label: 'EMERGENCY', icon: 'warning', bg: 'bg-error', text: 'text-on-error' },
  urgent:    { label: 'URGENT',    icon: 'priority_high', bg: 'bg-[#FFB4A1]', text: 'text-[#650B00]'  },
  soon:      { label: 'SEE SOON',  icon: 'schedule', bg: 'bg-tertiary', text: 'text-on-tertiary'  },
  routine:   { label: 'ROUTINE',   icon: 'check_circle', bg: 'bg-primary-container', text: 'text-on-primary-container'  },
  self_care: { label: 'SELF CARE', icon: 'home', bg: 'bg-surface-variant', text: 'text-on-surface-variant'  },
}

export default function UrgencyBadge({ level }) {
  const config = URGENCY_CONFIG[level] || URGENCY_CONFIG.routine

  return (
    <div className={`inline-flex items-center gap-xs px-sm py-[4px] rounded-full ${config.bg} ${config.text} w-fit`}>
      <span className="material-symbols-outlined text-[16px]">{config.icon}</span>
      <span className="text-label-sm font-label-sm font-bold tracking-wider">{config.label}</span>
    </div>
  )
}
