<template>
	<span class="self-center text-p-sm text-ink-gray-5">{{ savedLabel }}</span>

	<template v-if="canChange">
		<DateTimePicker
			:model-value="post.scheduled_at ?? ''"
			:min="dayjs().format('YYYY-MM-DD HH:mm:ss')"
			:clearable="false"
			@update:model-value="setTime"
		>
			<!-- A post is scheduled by picking a time, so the time is the button. The picker
			opens itself only for its own input, so a trigger of ours has to say when. -->
			<template #trigger="{ open, setOpen }">
				<Button
					icon-left="lucide-calendar-clock"
					:label="timeLabel"
					:active="open"
					:loading="schedule.loading || reschedule.loading"
					aria-label="Schedule"
					@click="setOpen(!open)"
				/>
			</template>
		</DateTimePicker>

		<Button
			v-if="post.status === 'Scheduled'"
			label="Unschedule"
			:loading="unschedule.loading"
			@click="takeOffTheClock"
		/>

		<Button
			variant="solid"
			theme="gray"
			label="Publish now"
			:loading="publish.loading"
			:disabled="!canPublish"
			:tooltip="canPublish ? undefined : 'Fix what the platforms flag first'"
			@click="askPublish"
		/>
	</template>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button, DateTimePicker, dayjs, dialog, toast, useCall } from 'frappe-ui'
import { errorMessage } from '@/lib/errors'
import { isLocked } from '@/lib/social'
import type { SocialPost, SocialPostStatus } from '@/types'

/**
 * What a post can do right now: pick a time, move it, drop it, or go out at once.
 * A post out or on its way out shows nothing here, because nothing can be done to it.
 */
const props = defineProps<{
	post: SocialPost
	/** Every target is happy with the content. The server checks again before anything goes out. */
	canPublish: boolean
	/** Where autosave got to, shown next to the actions. */
	savedLabel: string
	/** How many channels the post goes to, for the confirmation. */
	channels: number
}>()

const emit = defineEmits<{ changed: [] }>()

const canChange = computed(() => !isLocked(props.post.status))

const timeLabel = computed(() =>
	props.post.scheduled_at ? dayjs(props.post.scheduled_at).format('D MMM, h:mm A') : 'Schedule',
)

function call(method: string) {
	return useCall<SocialPostStatus, { post: string; scheduled_at?: string }>({
		url: `/api/v2/method/bwh_os.social.api.${method}`,
		method: 'POST',
		immediate: false,
	})
}

const schedule = call('schedule_post')
const reschedule = call('reschedule_post')
const unschedule = call('unschedule_post')
const publish = call('publish_post')

/** A draft takes the time and goes on the clock. A scheduled post only moves. */
async function setTime(at: string) {
	if (!at) return
	const scheduled = props.post.status === 'Scheduled'
	await run(scheduled ? reschedule : schedule, { post: props.post.name, scheduled_at: at })
	toast.success(scheduled ? 'Time changed' : `Scheduled for ${dayjs(at).format('D MMM, h:mm A')}`)
}

async function takeOffTheClock() {
	await run(unschedule, { post: props.post.name })
	toast.success('Back to a draft')
}

function askPublish() {
	dialog.confirm({
		title: 'Publish now',
		message: `This goes out to ${
			props.channels === 1 ? 'the channel' : `${props.channels} channels`
		} right away.`,
		confirmLabel: 'Publish',
		onConfirm: async () => {
			await run(publish, { post: props.post.name })
			toast.success('Publishing')
		},
	})
}

/** Every action ends the same way: say what went wrong, or tell the page to reload. */
async function run(resource: ReturnType<typeof call>, params: { post: string; scheduled_at?: string }) {
	try {
		await resource.submit(params)
	} catch (error) {
		toast.error(errorMessage(error as Error))
		throw error
	}
	emit('changed')
}
</script>
