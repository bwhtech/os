export type SubscriberStatus = 'Pending' | 'Active' | 'Unsubscribed' | 'Bounced'

export interface Subscriber {
	name: string
	email: string
	first_name: string | null
	status: SubscriberStatus
	subscribed_on: string | null
	tags: { tag: string }[]
}

export interface SubscriberTag {
	name: string
	tag_name: string
}
