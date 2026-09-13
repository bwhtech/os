import type { NumberCardProps } from 'frappe-ui/charts'
import type { Activity } from '@/types'

/** The last 30 days, with the change against the 30 before and a bar per week. */
export function lastPeriodCard(title: string, activity: Activity | null | undefined): NumberCardProps {
	return {
		title,
		value: activity?.last_period ?? null,
		delta: activity ? activity.last_period - activity.previous_period : null,
		deltaCaption: 'vs previous 30 days',
		sparkline: activity ? { data: activity.weekly.map((row) => row.count), type: 'bar' } : undefined,
	}
}

export function totalCard(title: string, activity: Activity | null | undefined): NumberCardProps {
	return { title, value: activity?.total ?? null, deltaCaption: 'All time' }
}
