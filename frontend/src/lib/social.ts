import type { SocialMedia, SocialPost, SocialPostPart, SocialPostStatus } from '@/types'

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

/** The media of a part. The document API hands JSON fields back as a string. */
export function mediaOf(part: Pick<SocialPostPart, 'media'>): SocialMedia[] {
	if (!part.media) return []
	return typeof part.media === 'string' ? JSON.parse(part.media) : part.media
}
