import type { SocialMedia, SocialPost, SocialPostPart, SocialPostStatus, SocialTargetStatus } from '@/types'

/** Grey while it waits, blue once it has a time, green when it is out, red when it is not. */
export const POST_STATUS_THEMES: Record<SocialPostStatus, 'gray' | 'blue' | 'amber' | 'green' | 'red'> = {
	Draft: 'gray',
	Scheduled: 'blue',
	Publishing: 'amber',
	Published: 'green',
	// Some targets made it and some did not, so the badge warns without calling it a failure.
	Partial: 'amber',
	Failed: 'red',
}

export const TARGET_THEMES: Record<SocialTargetStatus, 'gray' | 'amber' | 'green' | 'red'> = {
	Pending: 'gray',
	Publishing: 'amber',
	Published: 'green',
	Failed: 'red',
}

/**
 * The colour a post takes on the calendar. The palette of the calendar has no grey and no
 * red, so a draft borrows blue and wears the dashed outline instead, and a failure takes
 * the closest thing to a warning the palette has.
 */
export const POST_CALENDAR_COLORS: Record<SocialPostStatus, string> = {
	Draft: 'blue',
	Scheduled: 'blue',
	Publishing: 'amber',
	Published: 'green',
	Partial: 'amber',
	Failed: 'pink',
}

/** Nothing has gone out yet, so the post is a plan: the calendar draws it dashed. */
export function isPlanned(status: SocialPostStatus): boolean {
	return status === 'Draft' || status === 'Scheduled'
}

/**
 * The moment a post belongs to on a calendar, or nothing when it belongs to no day.
 * What happened beats what was planned, as `bwh_os.social.api.calendar_time` does.
 */
export function postTime(post: Pick<SocialPost, 'scheduled_at' | 'published_at'>): string | null {
	return post.published_at || post.scheduled_at || null
}

/** A post that is out, or on its way out, cannot be written any more. */
export function isLocked(status: SocialPostStatus | undefined): boolean {
	return Boolean(status) && status !== 'Draft' && status !== 'Scheduled'
}

/** Anything that changes the list page or the composer. */
export const SOCIAL_DOCTYPES = ['Social Post', 'Social Channel']

export function postRoute(post: Pick<SocialPost, 'name'> | string): string {
	return `/social/${typeof post === 'string' ? post : post.name}`
}

/**
 * The parts of one group, in order. An empty channel is the content every target uses;
 * a channel is the content written for that channel alone.
 */
export function partsOf(
	post: SocialPost | null | undefined,
	channel: string | null = null,
): SocialPostPart[] {
	return (post?.parts ?? [])
		.filter((part) => (part.channel || null) === channel)
		.sort((a, b) => a.part_no - b.part_no)
}

/** One part as the composer holds it: the text and the images, with no row bookkeeping. */
export interface DraftPart {
	text: string
	media: SocialMedia[]
}

/** One group of parts, ready for the editor. A group with nothing in it starts with one part. */
export function draftPartsOf(
	post: SocialPost | null | undefined,
	channel: string | null = null,
): DraftPart[] {
	const parts = partsOf(post, channel).map((part) => ({ text: part.text ?? '', media: mediaOf(part) }))
	return parts.length ? parts : [{ text: '', media: [] }]
}

/** The media of a part. The document API hands JSON fields back as a string. */
export function mediaOf(part: Pick<SocialPostPart, 'media'>): SocialMedia[] {
	if (!part.media) return []
	return typeof part.media === 'string' ? JSON.parse(part.media) : part.media
}
