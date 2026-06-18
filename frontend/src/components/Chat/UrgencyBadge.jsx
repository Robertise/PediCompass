/**
 * UrgencyBadge — color-coded urgency level indicator.
 * Emergency level includes a CSS pulse animation.
 */

const URGENCY_CONFIG = {
  emergency: { label: '🔴 Emergency', icon: '🚨' },
  urgent:    { label: '🟠 Urgent',    icon: '⚠️'  },
  soon:      { label: '🟡 See Soon',  icon: '⏰'  },
  routine:   { label: '🟢 Routine',   icon: '✅'  },
  self_care: { label: '🟢 Self Care', icon: '🏠'  },
}

/**
 * @param {Object} props
 * @param {'emergency'|'urgent'|'soon'|'routine'|'self_care'} props.level
 * @param {'sm'|'md'|'lg'} [props.size='md']
 */
export default function UrgencyBadge({ level, size = 'md' }) {
  const config = URGENCY_CONFIG[level] || URGENCY_CONFIG.routine

  const sizeStyles = {
    sm: { fontSize: '0.75rem', padding: '4px 10px' },
    md: {},
    lg: { fontSize: '1rem', padding: '10px 20px' },
  }

  return (
    <span
      className={`urgency-badge urgency-badge--${level}`}
      style={sizeStyles[size]}
      role="status"
      aria-label={`Urgency level: ${config.label}`}
    >
      {config.label}
    </span>
  )
}
