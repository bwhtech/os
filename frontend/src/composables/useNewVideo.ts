import { useRouter } from 'vue-router'
import { dialog, useCall } from 'frappe-ui'
import { useVideoSeries } from '@/composables/useVideoSeries'
import { videoRoute } from '@/lib/videos'
import type { Video } from '@/types'

/**
 * Asks for a title and opens the new video. Pass a series to add the video to it,
 * or leave it out to let the user pick one. A new video is always an Idea.
 */
export function useNewVideo() {
	const router = useRouter()
	const { series } = useVideoSeries()

	const insert = useCall<Video, { title: string; series: string | null }>({
		url: '/api/v2/document/BWH Video',
		method: 'POST',
		immediate: false,
	})

	function open(seriesName?: string) {
		dialog.prompt({
			title: 'New Video',
			confirmLabel: 'Create',
			fields: seriesName ? [TITLE_FIELD] : [TITLE_FIELD, seriesField()],
			onConfirm: async ({ values }) => {
				const video = await insert.submit({
					title: values.title.trim(),
					series: seriesName ?? (values.series || null),
				})
				if (video) router.push(videoRoute(video))
			},
		})
	}

	function seriesField() {
		const options = (series.data ?? []).map((row) => ({ label: row.title, value: String(row.name) }))
		return {
			name: 'series',
			label: 'Series',
			type: 'select' as const,
			defaultValue: '',
			description: 'Leave empty for a one-off video. You can move it into a series later.',
			options: [{ label: 'None', value: '' }, ...options],
		}
	}

	return { open }
}

const TITLE_FIELD = { name: 'title', label: 'Working title', required: true }
