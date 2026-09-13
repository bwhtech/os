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
	double_opt_in: 0 | 1
	confirm_subject: string | null
	confirm_body: string | null
	success_message: string
	tags: TagRow[]
	lead_magnet: string | null
	welcome_subject: string | null
	welcome_body: string | null
}

export interface LeadMagnet {
	name: string
	title: string
	description: string | null
	/** Private file URL */
	file: string
}
