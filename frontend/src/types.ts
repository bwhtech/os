import type { JSONContent } from '@tiptap/core'

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

export type ImportField = 'email' | 'first_name' | 'full_name' | 'tags'

/** CSV header name per subscriber field. Null means the field is not imported. */
export type ImportMapping = Record<ImportField, string | null>

export type ImportAction = 'New' | 'Existing' | 'Invalid' | 'Duplicate'

export type ImportCounts = Record<ImportAction, number>

export interface ImportPreview {
	columns: { name: string; samples: string[] }[]
	mapping: ImportMapping
	total: number
	counts: ImportCounts
	/** The first rows of the file, as they will import */
	rows: { email: string; first_name: string | null; tags: string[]; action: ImportAction }[]
}

/** Payload of the `subscriber_import_progress` realtime event */
export interface ImportProgressEvent {
	import_id: string
	status: 'Running' | 'Done' | 'Failed'
	done: number
	total: number
	counts: ImportCounts & { Failed: number }
	/** The first failed rows */
	errors: { email: string; error: string }[]
	/** Why the whole import failed */
	message: string | null
}

/** A TipTap document from the newsletter editor */
export type EmailDocument = JSONContent

export type NewsletterStatus = 'Draft' | 'Scheduled' | 'Sending' | 'Sent' | 'Failed'

export type NewsletterTheme = 'Frappe UI' | 'Basic' | 'Minimal'

export interface NewsletterIssue {
	name: string
	subject: string
	preview_text: string | null
	status: NewsletterStatus
	theme: NewsletterTheme
	/** The API returns JSON fields as a string */
	content_json: string | EmailDocument | null
	content_html: string | null
	modified: string
}
