export type SubscriberStatus = 'Pending' | 'Active' | 'Unsubscribed' | 'Bounced'

export interface TagRow {
	tag: string
}

export interface Subscriber {
	name: string
	email: string
	first_name: string | null
	status: SubscriberStatus
	source_form: string | null
	subscribed_on: string | null
	tags: TagRow[]
}

export interface SubscriberTag {
	name: string
	tag_name: string
}

export interface SignupForm {
	name: string
	title: string
	form_id: string
	is_active: 0 | 1
	collect_name: 0 | 1
	success_message: string
	tags: TagRow[]
}
