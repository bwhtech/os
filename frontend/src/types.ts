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
	confirm_theme: NewsletterTheme
	/** The API returns JSON fields as a string */
	confirm_content_json: string | EmailDocument | null
	confirm_content_html: string | null
	success_message: string
	tags: TagRow[]
	lead_magnet: string | null
	welcome_subject: string | null
	welcome_theme: NewsletterTheme
	welcome_content_json: string | EmailDocument | null
	welcome_content_html: string | null
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
	audience: NewsletterAudience
	tags: TagRow[]
	hourly_limit: number
	scheduled_at: string | null
	sent_at: string | null
	completed_at: string | null
	recipient_count: number
	sent_count: number
	failed_count: number
	skipped_count: number
	opened_count: number
	clicked_count: number
	unsubscribed_count: number
	/** Shown in the web archive at /newsletter/<route> */
	is_public: 0 | 1
	route: string | null
	modified: string
}

export type NewsletterAudience = 'All Active' | 'Tags'

/** Who a send would reach, from `get_newsletter_audience` */
export interface AudiencePreview {
	recipients: number
	/** Subscribers who match the audience but are not Active, by status */
	left_out: Partial<Record<SubscriberStatus, number>>
	hourly_limit: number
	/** Emails in each hourly batch, first batch first */
	batches: number[]
}

export type DeliveryStatus = 'Queued' | 'Sent' | 'Failed' | 'Skipped'

export interface NewsletterDelivery {
	name: string
	email: string
	status: DeliveryStatus
	batch: number
	error: string | null
}

/** From `get_newsletter_progress` */
export interface NewsletterProgress {
	counts: Record<DeliveryStatus, number>
	batches: ({ batch: number; sends_at: string | null } & Record<DeliveryStatus, number>)[]
}

/** Rates are 0 to 100, or null when nothing was sent */
export interface EngagementRates {
	open_rate: number | null
	click_rate: number | null
	unsubscribes: number
}

/** The rates of an issue and of the issue sent before it */
export interface EngagementComparison {
	rates: EngagementRates
	previous: ({ name: string; subject: string } & EngagementRates) | null
}

/** From `get_newsletter_engagement` */
export interface NewsletterEngagement extends EngagementComparison {
	funnel: { stage: string; count: number }[]
	/** One row per hour from the start of the send, for 72 hours */
	hourly: { hour: number; Open: number; Click: number }[]
	top_links: { url: string; clicks: number; readers: number }[]
}

export interface MailingSettings {
	name: 'Mailing Settings'
	email_account: string | null
	default_hourly_limit: number
	company_name: string | null
	gstin: string | null
	postal_address: string | null
	youtube_url: string | null
	x_url: string | null
	linkedin_url: string | null
	github_url: string | null
	discord_url: string | null
	notify_blog_comments: 0 | 1
	blog_notification_email: string | null
}

export interface LMSSyncSettings {
	name: 'LMS Sync Settings'
	enabled: 0 | 1
	site_url: string | null
	api_key: string | null
	/** Asterisks when a secret is saved */
	api_secret: string | null
	user_tags: { tag: string }[]
	enrollment_tags: { tag: string }[]
	/** In the LMS site's time zone */
	users_synced_until: string | null
	enrollments_synced_until: string | null
	last_synced_on: string | null
	last_sync_status: '' | 'Success' | 'Failed' | null
	last_sync_message: string | null
}

/** From `bwh_os.mailing.api.sync_lms_now`. The counts are there only on success. */
export interface LMSSyncResult {
	status: 'Success' | 'Failed'
	message: string
	added?: number
	skipped?: number
	failed?: number
	tagged?: number
}

/** Counts from `bwh_os.mailing.stats.activity` */
export interface Activity {
	total: number
	/** The last 30 days, today included */
	last_period: number
	/** The 30 days before that */
	previous_period: number
	/** The last 12 weeks, oldest first. `week` is the Monday. */
	weekly: { week: string; count: number }[]
}

/** From `get_form_confirmations` */
export interface FormConfirmations {
	signups: number
	confirmed: number
	/** 0 to 100, or null with no signups */
	confirm_rate: number | null
}

export interface ListOverview {
	subscribers: Activity
	/** Unsubscribed subscribers, dated by `unsubscribed_on` */
	unsubscribes: Activity
	downloads: Activity
	by_status: { value: SubscriberStatus; count: number }[]
	/** Biggest form first. `confirm_rate` is null for single opt-in and for subscribers with no form. */
	by_form: { form: string; signups: number; confirmed: number; confirm_rate: number | null }[]
	/** The last Sent issue */
	last_issue: ({ name: string; subject: string; sent_at: string; recipient_count: number } & EngagementComparison) | null
	/** The last 10 Sent issues, oldest first */
	issue_rates: ({ name: string; subject: string; sent_at: string } & EngagementRates)[]
}

/** A `BWH Blog Comment` row */
export interface BlogComment {
	/** Autoincrement. The server sends a number, and useList types every name as a string. */
	name: string
	post: string
	commenter_name: string
	email: string
	body: string
	hidden: 0 | 1
	creation: string
}

/** A `BWH Blog Post` row */
export interface BlogPostRow {
	name: string
	title: string | null
	likes: number
}

/** A post with its comments, for the Comments page */
export interface BlogPost {
	post_id: string
	title: string
	url: string
	likes: number
	/** Newest first */
	comments: BlogComment[]
}

export interface BlogTopPost {
	post_id: string
	title: string | null
	count: number
}

/** From `bwh_os.blog.api.get_overview` */
export interface BlogOverview {
	comments: Activity
	hidden: number
	likes: number
	top_by_comments: BlogTopPost[]
	top_by_likes: BlogTopPost[]
}

export type VideoStatus =
	| 'Idea'
	| 'Researching'
	| 'Scripting'
	| 'Recording'
	| 'Editing'
	| 'Thumbnail Pending'
	| 'Published'

/** A `BWH Video` */
export interface Video {
	/** Autoincrement. The server sends a number, and useList types every name as a string. */
	name: string
	title: string
	status: VideoStatus
	series: string | null
	/** Order in the series, from 1. 0 without a series. The server sets it. */
	position: number
	publish_on: string | null
	youtube_url: string | null
	research: string | null
	script: string | null
	description: string | null
	modified: string
}

/** A `BWH Video Series` */
export interface VideoSeries {
	name: string
	title: string
	emoji: string | null
	summary: string | null
	notes: string | null
}

/** From `bwh_os.videos.api.get_series` */
export interface VideoSeriesSummary {
	name: number
	title: string
	emoji: string | null
	summary: string | null
	video_count: number
	published_count: number
}

/** A `File` attached to a video. A link is a File whose URL points outside the site. */
export interface VideoFile {
	name: string
	file_name: string | null
	file_url: string
	file_size: number
	is_private: 0 | 1
}

export type SocialProvider = 'LinkedIn' | 'X'

export type SocialChannelStatus = 'Connected' | 'Expired' | 'Disconnected'

/** A `Social Channel`, from `bwh_os.social.api.get_channels` */
export interface SocialChannel {
	name: string
	provider: SocialProvider
	display_name: string | null
	handle: string | null
	avatar_url: string | null
	profile_url: string | null
	status: SocialChannelStatus
	connected_on: string | null
	expires_on: string | null
	last_error: string | null
	/** Whole days until the token expires. Null when the channel has no expiry. */
	days_left: number | null
}

/** The OAuth app of a platform, from `bwh_os.social.api.get_provider_apps` */
export interface SocialProviderApp {
	provider: SocialProvider
	/** The name of the `Connected App` */
	app: string
	/** The URI to register in the console of the platform */
	redirect_uri: string
	scopes: string[]
	client_id: string | null
	has_credentials: boolean
}

export type SocialPostStatus = 'Draft' | 'Scheduled' | 'Publishing' | 'Published' | 'Partial' | 'Failed'

export type SocialTargetStatus = 'Pending' | 'Publishing' | 'Published' | 'Failed'

export type SocialErrorKind = '' | 'Reconnect' | 'Bad Request' | 'Retryable' | 'Unconfirmed'

/** One file on a part. The server keeps it as JSON. */
export interface SocialMedia {
	file_url: string
	kind: 'image' | 'video'
}

/** A `Social Post Target` row: one channel this post goes to */
export interface SocialPostTarget {
	name?: string
	channel: string
	provider: SocialProvider
	use_custom_content: 0 | 1
	/** The API returns JSON fields as a string */
	settings: string | Record<string, unknown> | null
	status: SocialTargetStatus
	release_id: string | null
	release_url: string | null
	published_at: string | null
	error: string | null
	error_kind: SocialErrorKind | null
}

/** A `Social Post Part` row. An empty `channel` is the content every target uses. */
export interface SocialPostPart {
	name?: string
	channel: string | null
	/** From 1 inside its group. The server sets it. */
	part_no: number
	text: string | null
	/** The API returns JSON fields as a string */
	media: string | SocialMedia[] | null
}

/** A `Social Post` */
export interface SocialPost {
	/** Autoincrement. The server sends a number, and useDoc types every name as a string. */
	name: string
	title: string | null
	status: SocialPostStatus
	scheduled_at: string | null
	published_at: string | null
	video: string | null
	targets: SocialPostTarget[]
	parts: SocialPostPart[]
	modified: string
}

/** A row of `bwh_os.social.api.get_posts`: the post with the channels it goes to */
export interface SocialPostRow {
	name: string
	title: string | null
	status: SocialPostStatus
	scheduled_at: string | null
	published_at: string | null
	video: string | null
	modified: string
	targets: {
		channel: string
		provider: SocialProvider
		status: SocialTargetStatus
		release_url: string | null
		display_name: string | null
		avatar_url: string | null
		channel_status: SocialChannelStatus | null
	}[]
}

/** One target's verdict, from `bwh_os.social.api.validate_post` */
export interface TargetValidation {
	channel: string
	provider: SocialProvider
	use_custom_content: boolean
	/** The character limit of the platform */
	limit: number
	/** How many images the platform takes in one part */
	max_images: number
	/** Whether the platform takes media on a part after the first */
	media_after_part_one: boolean
	/** The length of each part, part 1 first */
	counts: number[]
	errors: string[]
}
