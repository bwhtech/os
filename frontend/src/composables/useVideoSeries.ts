import { computed } from 'vue'
import { debounce, useCall } from 'frappe-ui'
import { onListUpdate } from '@/lib/socket'
import { VIDEO_DOCTYPES } from '@/lib/videos'
import type { VideoSeriesSummary } from '@/types'

/** Every series with its counts. Reloads when any video or series changes. */
export function useVideoSeries() {
	const series = useCall<VideoSeriesSummary[]>({
		url: '/api/v2/method/bwh_os.videos.api.get_series',
		cacheKey: 'bwh-video-series',
	})

	onListUpdate(VIDEO_DOCTYPES, debounce(() => series.reload(), 300))

	/** Keyed by the name as a string, because Link fields hold the name as a string. */
	const byName = computed<Record<string, VideoSeriesSummary>>(() =>
		Object.fromEntries((series.data ?? []).map((row) => [String(row.name), row])),
	)

	return { series, byName }
}
