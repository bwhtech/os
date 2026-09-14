import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { debounce, toast, useCall, useList } from 'frappe-ui'
import { errorMessage } from '@/lib/errors'
import { onListUpdate } from '@/lib/socket'
import type { Video } from '@/types'

export type SeriesVideo = Pick<Video, 'name' | 'title' | 'status' | 'series' | 'position' | 'publish_on'>

/** The videos of a series in their order, and a way to change the order. */
export function useSeriesVideos(series: MaybeRefOrGetter<string>) {
	const list = useList<SeriesVideo>({
		doctype: 'BWH Video',
		fields: ['name', 'title', 'status', 'series', 'position', 'publish_on'],
		filters: () => ({ series: toValue(series) }),
		orderBy: 'position asc',
		limit: 500,
	})

	const moveCall = useCall<number[], { video: string; position: number }>({
		url: '/api/v2/method/bwh_os.videos.api.move_video',
		method: 'POST',
		immediate: false,
	})

	onListUpdate(['BWH Video'], debounce(() => list.reload(), 300))

	// Sorted here too, so a local reorder shows before the reload.
	const videos = computed(() => [...(list.data ?? [])].sort((a, b) => a.position - b.position))
	const published = computed(() => videos.value.filter((video) => video.status === 'Published').length)

	/** Put `video` where `target` is. The list reorders at once and the server confirms. */
	async function move(video: SeriesVideo, target: SeriesVideo) {
		if (video.name === target.name) return
		// Read it first: the local reorder renumbers the rows in place.
		const position = target.position
		reorderLocally(video, position)
		try {
			await moveCall.submit({ video: String(video.name), position })
		} catch (error) {
			toast.error(errorMessage(error as Error))
		}
		list.reload()
	}

	/** The same steps as `SeriesOrder.move` on the server. */
	function reorderLocally(video: SeriesVideo, position: number) {
		const order = [...videos.value]
		order.splice(order.indexOf(video), 1)
		order.splice(position - 1, 0, video)
		order.forEach((row, index) => list.updateRow({ ...row, position: index + 1 }))
	}

	return { list, videos, published, move }
}
