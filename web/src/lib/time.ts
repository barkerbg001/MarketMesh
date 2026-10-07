const relative = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' })
const absolute = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' })

const STEPS: [Intl.RelativeTimeFormatUnit, number][] = [
  ['year', 31_536_000],
  ['month', 2_592_000],
  ['week', 604_800],
  ['day', 86_400],
  ['hour', 3_600],
  ['minute', 60],
]

export function timeAgo(iso: string | null | undefined, now = Date.now()) {
  if (!iso) return 'unknown time'
  const seconds = Math.round((new Date(iso).getTime() - now) / 1000)
  if (!Number.isFinite(seconds)) return 'unknown time'
  for (const [unit, size] of STEPS) {
    if (Math.abs(seconds) >= size) return relative.format(Math.round(seconds / size), unit)
  }
  return 'just now'
}

export function formatDateTime(iso: string | null | undefined) {
  if (!iso) return 'Unknown'
  const date = new Date(iso)
  return Number.isNaN(date.getTime()) ? 'Unknown' : absolute.format(date)
}
