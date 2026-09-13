import type { NumberCardProps } from 'frappe-ui/charts'
import type { EngagementComparison } from '@/types'

/** Open rate, click rate, and unsubscribes of an issue, each against the issue before it. */
export function engagementCards(comparison: EngagementComparison | null | undefined): NumberCardProps[] {
	const rates = comparison?.rates
	const previous = comparison?.previous
	const deltaCaption = previous ? `vs ${previous.subject}` : 'No earlier issue'
	return [
		{
			title: 'Open rate',
			value: rates?.open_rate ?? null,
			suffix: '%',
			...change(rates?.open_rate, previous?.open_rate, ' pts'),
			deltaCaption,
		},
		{
			title: 'Click rate',
			value: rates?.click_rate ?? null,
			suffix: '%',
			...change(rates?.click_rate, previous?.click_rate, ' pts'),
			deltaCaption,
		},
		{
			title: 'Unsubscribes',
			value: rates?.unsubscribes ?? null,
			...change(rates?.unsubscribes, previous?.unsubscribes),
			negativeIsBetter: true,
			deltaCaption,
		},
	]
}

function change(current: number | null | undefined, previous: number | null | undefined, suffix = '') {
	if (current == null || previous == null) return {}
	return { delta: Math.round((current - previous) * 10) / 10, deltaSuffix: suffix }
}
