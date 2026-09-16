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

/** The shared parts of a post, ready for the editor. A post with none starts with one. */
export function draftPartsOf(post: SocialPost | null | undefined): DraftPart[] {
	const parts = partsOf(post).map((part) => ({ text: part.text ?? '', media: mediaOf(part) }))
	return parts.length ? parts : [{ text: '', media: [] }]
}

/** The media of a part. The document API hands JSON fields back as a string. */
export function mediaOf(part: Pick<SocialPostPart, 'media'>): SocialMedia[] {
	if (!part.media) return []
	return typeof part.media === 'string' ? JSON.parse(part.media) : part.media
}
