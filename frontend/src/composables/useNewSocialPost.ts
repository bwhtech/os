import { useRouter } from 'vue-router'
import { toast, useCall } from 'frappe-ui'
import { useSocialChannels } from '@/composables/useSocialChannels'
import { errorMessage } from '@/lib/errors'
import { postRoute } from '@/lib/social'
import type { SocialPost } from '@/types'

/**
 * Makes a draft and opens it. A new post starts as a Draft for every connected channel,
 * so the composer has a document from the first keystroke and attachments have somewhere
 * to go. A time makes the draft sit on that day in the calendar; it goes out only once
 * someone schedules it.
 */
export function useNewSocialPost() {
	const router = useRouter()
	const { connected } = useSocialChannels()

	const insert = useCall<SocialPost, Partial<SocialPost>>({
		url: '/api/v2/document/Social Post',
		method: 'POST',
		immediate: false,
	})

	async function create(scheduledAt?: string) {
		try {
			const post = await insert.submit({
				status: 'Draft',
				scheduled_at: scheduledAt ?? null,
				targets: connected.value.map((channel) => ({
					channel: channel.name,
				})) as SocialPost['targets'],
				parts: [{ text: '' }] as SocialPost['parts'],
			})
			if (post) router.push(postRoute(post))
		} catch (error) {
			toast.error(errorMessage(error as Error))
		}
	}

	return { create, insert }
}
