import { ref, watch } from 'vue'
import { debounce, useCall } from 'frappe-ui'
import type { AudiencePreview, NewsletterAudience } from '@/types'

export interface AudienceDraft {
	audience: NewsletterAudience
	tags: string[]
	hourlyLimit: number
}

/** The live audience of an issue, from the unsaved values on the page. */
export function useAudiencePreview(draft: () => AudienceDraft) {
	const params = ref(toParams(draft()))

	// Typing an hourly limit fires a request per key without the debounce.
	watch(
		() => JSON.stringify(toParams(draft())),
		debounce(() => {
			params.value = toParams(draft())
		}, 300),
	)

	return useCall<AudiencePreview, ReturnType<typeof toParams>>({
		url: '/api/v2/method/bwh_os.mailing.api.get_newsletter_audience',
		method: 'GET',
		params: () => params.value,
		refetch: true,
	})
}

function toParams({ audience, tags, hourlyLimit }: AudienceDraft) {
	// A GET request sends a list as "a,b", so the tags go as a JSON array.
	return { audience, tags: JSON.stringify(tags), hourly_limit: hourlyLimit || 0 }
}
