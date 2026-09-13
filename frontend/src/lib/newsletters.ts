import type { NewsletterStatus } from '@/types'

export const STATUS_THEMES: Record<NewsletterStatus, 'gray' | 'blue' | 'amber' | 'green' | 'red'> = {
	Draft: 'gray',
	Scheduled: 'blue',
	Sending: 'amber',
	Sent: 'green',
	Failed: 'red',
}
