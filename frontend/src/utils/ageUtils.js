/**
 * Client-side age utilities for PediCompass frontend.
 * Mirrors common/age_utils.py logic for UI display purposes.
 */

/**
 * Calculate age in days from a DOB ISO string ("YYYY-MM-DD").
 * Returns null if dob is falsy.
 */
export function ageDaysFromDob(dob) {
  if (!dob) return null
  const birth = new Date(dob)
  const now = new Date()
  const diffMs = now - birth
  return Math.floor(diffMs / (1000 * 60 * 60 * 24))
}

/**
 * Convert age in days to a human-readable display string.
 * @param {number} ageDays
 * @returns {string}  e.g. "14 days old", "3 months old", "2 years 1 month old"
 */
export function ageDaysToDisplay(ageDays) {
  if (ageDays === null || ageDays === undefined) return 'Unknown age'

  if (ageDays < 28) {
    return `${ageDays} ${ageDays === 1 ? 'day' : 'days'} old`
  }

  if (ageDays < 365) {
    const months = Math.floor(ageDays / 30)
    return `${months} ${months === 1 ? 'month' : 'months'} old`
  }

  const years = Math.floor(ageDays / 365)
  const remainingMonths = Math.floor((ageDays % 365) / 30)
  if (remainingMonths > 0) {
    return `${years} ${years === 1 ? 'year' : 'years'} ${remainingMonths} ${remainingMonths === 1 ? 'month' : 'months'} old`
  }
  return `${years} ${years === 1 ? 'year' : 'years'} old`
}

/**
 * Map age in days to clinical age group label.
 * Mirrors age_utils.py:map_age_to_group()
 */
export function mapAgeToGroup(ageDays) {
  if (ageDays === null || ageDays === undefined) return null
  if (ageDays <= 28)   return 'newborn'
  if (ageDays <= 90)   return 'young_infant'
  if (ageDays <= 365)  return 'infant'
  if (ageDays <= 1095) return 'toddler'
  return 'preschool'
}

/**
 * Check if a child profile's data is stale (last_updated > 30 days ago).
 * Used to show the "please update your profile" reminder.
 */
export function isProfileStale(lastUpdated) {
  if (!lastUpdated) return false
  const updated = new Date(lastUpdated)
  const now = new Date()
  const diffDays = Math.floor((now - updated) / (1000 * 60 * 60 * 24))
  return diffDays > 30
}

/**
 * Age group human-readable labels for display.
 */
export const AGE_GROUP_LABELS = {
  newborn:      'Newborn (0–28 days)',
  young_infant: 'Young Infant (1–3 months)',
  infant:       'Infant (3–12 months)',
  toddler:      'Toddler (1–3 years)',
  preschool:    'Preschool (3–5 years)',
}
