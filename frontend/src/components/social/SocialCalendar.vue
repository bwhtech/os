<template>
	<div ref="root" class="flex min-h-0 flex-col" :style="{ height }">
		<ErrorMessage v-if="posts.error" :message="errorMessage(posts.error)" />
		<Calendar
			:events="events"
			:config="CONFIG"
			:on-click="open"
			:on-dbl-click="open"
			:on-cell-click="draftOn"
			@update="moved"
			@range-change="setRange"
		/>
	</div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ErrorMessage, dayjs, debounce, toast, useCall, useList } from 'frappe-ui'
import { Calendar } from 'frappe-ui/experimental'
import type { CalendarCellClickData, CalendarConfig, CalendarEvent } from 'frappe-ui/experimental'
import { useFillViewport } from '@/composables/useFillViewport'
import { useNewSocialPost } from '@/composables/useNewSocialPost'
import { errorMessage } from '@/lib/errors'
import { onListUpdate } from '@/lib/socket'
import { POST_CALENDAR_COLORS, SOCIAL_DOCTYPES, isPlanned, postRoute, postTime } from '@/lib/social'
import { VIDEO_DOCTYPES, videoRoute } from '@/lib/videos'
import type { SocialPostRow, Video } from '@/types'

/**
 * One month of the pipeline: the posts going out and the videos they promote, on the same
 * grid. Dragging a post moves its time, dragging a video moves its publish day, and a
 * click on an empty day starts a draft for it.
 */
const CONFIG: Partial<CalendarConfig> = {
	// A month is how a pipeline is read. The Day view is left in the switcher because a
	// click on a date number opens it whether or not the switcher offers it.
	defaultMode: 'Month',
	isEditMode: true,
}

/** How long a post sits on the hour grid of the Week view. A post takes no time at all. */
const SLOT_MINUTES = 30

/** The hour a day gets when the click that made the draft named no time. */
const DEFAULT_HOUR = 10

const router = useRouter()
const { create } = useNewSocialPost()

const root = ref<HTMLElement | null>(null)
const { height } = useFillViewport(root)

/** The days the calendar is showing. The Month view reports the padding days too. */
const range = ref({
	start: dayjs().startOf('month').format('YYYY-MM-DD'),
	end: dayjs().endOf('month').format('YYYY-MM-DD'),
})

const posts = useCall<SocialPostRow[], { start: string; end: string }>({
	url: '/api/v2/method/bwh_os.social.api.get_calendar_posts',
	params: () => range.value,
})

const videos = useList<Video>({
	doctype: 'BWH Video',
	fields: ['name', 'title', 'status', 'series', 'publish_on'],
	filters: () => ({ publish_on: ['between', [range.value.start, range.value.end]] }),
	limit: 200,
})

onListUpdate(
	[...SOCIAL_DOCTYPES, ...VIDEO_DOCTYPES],
	debounce(() => {
		posts.reload()
		videos.reload()
	}, 300),
)

function setRange(payload: { startDate: string; endDate: string }) {
	range.value = { start: payload.startDate, end: payload.endDate }
}

const events = computed<CalendarEvent[]>(() => [
	...(posts.data ?? []).flatMap(postEvent),
	...(videos.data ?? []).map(videoEvent),
])

/** A post with no time belongs to no day. The list page is where those live. */
function postEvent(post: SocialPostRow): CalendarEvent[] {
	const at = postTime(post)
	if (!at) return []
	const start = dayjs(at)
	const end = start.add(SLOT_MINUTES, 'minute')
	return [
		{
			id: `post:${post.name}`,
			doc: post.name,
			kind: 'post',
			title: post.title || 'Untitled post',
			fromDate: start.format('YYYY-MM-DD'),
			// A late evening post would otherwise end on the next day and draw as a bar.
			toDate: start.format('YYYY-MM-DD'),
			fromTime: start.format('HH:mm'),
			toTime: end.isAfter(start.endOf('day')) ? '23:59' : end.format('HH:mm'),
			color: POST_CALENDAR_COLORS[post.status],
			isDraft: isPlanned(post.status),
		},
	]
}

/** The video the posts are for. A whole day, because a publish day is all it has. */
function videoEvent(video: Video): CalendarEvent {
	return {
		id: `video:${video.name}`,
		doc: String(video.name),
		kind: 'video',
		series: video.series,
		title: video.title,
		fromDate: video.publish_on as string,
		toDate: video.publish_on as string,
		isFullDay: true,
		color: 'orange',
		isDraft: video.status !== 'Published',
	}
}

function open({ calendarEvent }: { calendarEvent: CalendarEvent }) {
	router.push(routeOf(calendarEvent))
}

function routeOf(event: CalendarEvent): string {
	const name = String(event.doc)
	return event.kind === 'video'
		? videoRoute({ name, series: (event.series as string | null) ?? null })
		: postRoute(name)
}

const reschedule = useCall<string, { post: string; scheduled_at: string }>({
	url: '/api/v2/method/bwh_os.social.api.reschedule_post',
	method: 'POST',
	immediate: false,
})

/**
 * A drag has already moved the card. The server has the last word on whether it may move
 * at all, so a refusal puts the card back where it was.
 */
async function moved(event: CalendarEvent) {
	try {
		if (event.kind === 'video') {
			await videos.setValue.submit({ name: String(event.doc), publish_on: event.fromDate })
			toast.success(`Publishing on ${dayjs(event.fromDate).format('D MMM')}`)
		} else {
			// The calendar hands times back as `HH:mm` or `HH:mm:ss`, and the server takes one shape.
			const at = dayjs(`${event.fromDate} ${event.fromTime || '00:00'}`)
			await reschedule.submit({
				post: String(event.doc),
				scheduled_at: at.format('YYYY-MM-DD HH:mm:ss'),
			})
			toast.success(`Moved to ${at.format('D MMM, h:mm A')}`)
		}
	} catch (error) {
		toast.error(errorMessage(error as Error))
	} finally {
		posts.reload()
		videos.reload()
	}
}

/** An empty day is an invitation. The draft holds the day and waits to be written. */
function draftOn({ date, time }: CalendarCellClickData) {
	const day = dayjs(date)
	const at = time ? dayjs(`${day.format('YYYY-MM-DD')} ${time}`) : day.hour(DEFAULT_HOUR).startOf('hour')
	create(at.format('YYYY-MM-DD HH:mm:ss'))
}
</script>
