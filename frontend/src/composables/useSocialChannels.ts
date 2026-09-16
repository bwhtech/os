import { computed } from 'vue'
import { debounce, useCall } from 'frappe-ui'
import { onListUpdate } from '@/lib/socket'
import type { SocialChannel } from '@/types'

/** Every channel the OS knows, and the ones that can take a post right now. */
export function useSocialChannels() {
	const channels = useCall<SocialChannel[]>({
		url: '/api/v2/method/bwh_os.social.api.get_channels',
		cacheKey: 'bwh-social-channels',
	})

	onListUpdate(
		['Social Channel'],
		debounce(() => channels.reload(), 300),
	)

	const connected = computed(() => (channels.data ?? []).filter((row) => row.status === 'Connected'))

	const byName = computed<Record<string, SocialChannel>>(() =>
		Object.fromEntries((channels.data ?? []).map((row) => [row.name, row])),
	)

	return { channels, connected, byName }
}
