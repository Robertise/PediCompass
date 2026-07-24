import { motion } from 'framer-motion'

/**
 * StaleProfileBanner — Borderless reminder card shown when a selected child profile
 * has not had its weight or medical details updated in >30 days.
 *
 * Design constraints:
 *   - Strictly 100% borderless (no border / border-* classes).
 *   - Soft elevation (bg-amber-500/10 dark:bg-amber-500/15 or bg-surface-container-high).
 *   - Matches M3 / Pedix layout tokens (rounded-2xl, shadow-soft).
 */
export default function StaleProfileBanner({ profile, daysStale, onUpdateWeight, onDismiss }) {
  if (!profile) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.3 }}
      className="max-w-[52rem] mx-auto w-full mb-md px-4 md:px-0"
    >
      <div className="bg-amber-500/10 dark:bg-amber-500/15 text-on-surface p-md rounded-[20px] shadow-soft flex flex-col sm:flex-row items-start sm:items-center gap-md relative overflow-hidden">        
      {/* Text Body */}
        <div className="flex-1 flex flex-col gap-0.5">
          <div className="flex items-center gap-xs font-label-md font-bold text-amber-700 dark:text-amber-300 text-sm">
            <span>Has {profile.nickname}'s weight changed?</span>
            <span className="bg-amber-500/20 text-amber-800 dark:text-amber-200 text-[11px] px-2 py-0.5 rounded-full font-mono">
              {daysStale} days ago
            </span>
          </div>
          <p className="text-body-sm font-body-sm text-on-surface-variant leading-relaxed">
            This profile was last updated over 30 days ago. Updating weight ensures accurate age and weight-stratified triage guidance.
          </p>
        </div>

        {/* Action Buttons (Borderless) */}
        <div className="flex items-center gap-xs shrink-0 self-end sm:self-center">
          <button
            onClick={onDismiss}
            className="px-4 py-3 rounded-full text-label-md font-label-md text-on-surface-variant hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
          >
            Remind Later
          </button>
          <button
            onClick={onUpdateWeight}
            className="px-4 py-3 rounded-full text-label-md font-label-md bg-primary text-on-primary hover:bg-primary-fixed-variant transition-colors shadow-sm font-bold flex items-center gap-1"
          >
            <span className="material-symbols-outlined text-[18px]">edit</span>
            Update Now
          </button>
        </div>

      </div>
    </motion.div>
  )
}
