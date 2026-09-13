<template>
	<Dialog :open="open" title="Send Newsletter" size="2xl" @update:open="emit('update:open', $event)">
		<template #default="{ close }">
			<div class="space-y-4">
				<p class="text-p-base text-ink-gray-6">
					Unsaved changes are saved first. After you send or schedule it, the newsletter cannot change.
				</p>

				<div class="flex flex-wrap items-end gap-3">
					<TabButtons v-model="when" :options="WHEN_OPTIONS" />
					<DateTimePicker
						v-if="when === 'later'"
						v-model="scheduledAt"
						:min="dayjs().format('YYYY-MM-DD HH:mm:ss')"
						placeholder="Pick a time"
						class="w-56"
						aria-label="Send at"
					/>
				</div>

				<div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
					<NumberCard v-for="card in cards" :key="card.title" v-bind="card" />
				</div>

				<section v-if="batchRows.length > 1" class="h-56 rounded-xl border border-outline-gray-1 px-4 py-3">
					<BarChart
						:data="batchRows"
						x="hour"
						y="emails"
						:series-config="{ emails: { label: 'Emails' } }"
						title="Emails per hour"
						:subtitle="`At most ${preview.data?.hourly_limit} an hour`"
					/>
				</section>

				<ErrorMessage :message="errorMessage(sendCall.error || scheduleCall.error)" />

				<div class="flex justify-end gap-2 pt-2">
					<Button label="Cancel" @click="close" />
					<Button
						variant="solid"
						theme="gray"
						:icon-left="when === 'later' ? 'lucide-calendar-clock' : 'lucide-send'"
						:label="submitLabel"
						:loading="sendCall.loading || scheduleCall.loading || saving"
						:disabled="!recipients || (when === 'later' && !scheduledAt)"
						@click="submit(close)"
					/>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Button, DateTimePicker, Dialog, ErrorMessage, TabButtons, dayjs, toast, useCall } from 'frappe-ui'
import { BarChart, NumberCard, type NumberCardProps } from 'frappe-ui/charts'
import { errorMessage } from '@/lib/errors'
import type { AudiencePreview, NewsletterStatus, SubscriberStatus } from '@/types'

const props = defineProps<{
	open: boolean
	issueId: string
	preview: { data: AudiencePreview | null; loading: boolean }
	/** Saves unsaved changes. Resolves false when the save failed. */
	save: () => Promise<boolean>
}>()
const emit = defineEmits<{ 'update:open': [open: boolean]; sent: [] }>()

const WHEN_OPTIONS = [
	{ label: 'Send now', value: 'now' },
	{ label: 'Schedule', value: 'later' },
]

const saving = ref(false)
const when = ref<'now' | 'later'>('now')
/** `YYYY-MM-DD HH:mm:ss` in the browser time, which the server reads as system time. */
const scheduledAt = ref('')

const sendCall = useCall<NewsletterStatus, { issue: string }>({
	url: '/api/v2/method/bwh_os.mailing.api.send_newsletter',
	method: 'POST',
	immediate: false,
})

const scheduleCall = useCall<NewsletterStatus, { issue: string; scheduled_at: string }>({
	url: '/api/v2/method/bwh_os.mailing.api.schedule_newsletter',
	method: 'POST',
	immediate: false,
})

watch(
	() => props.open,
	(open) => {
		if (!open) return
		sendCall.reset()
		scheduleCall.reset()
		when.value = 'now'
		scheduledAt.value = dayjs().add(1, 'hour').startOf('hour').format('YYYY-MM-DD HH:mm:ss')
	},
)

const recipients = computed(() => props.preview.data?.recipients ?? 0)

const submitLabel = computed(() => {
	if (when.value === 'later') {
		return scheduledAt.value ? `Schedule for ${dayjs(scheduledAt.value).format('D MMM, h:mm A')}` : 'Schedule'
	}
	return `Send to ${recipients.value} ${recipients.value === 1 ? 'subscriber' : 'subscribers'}`
})

const batchRows = computed(() =>
	(props.preview.data?.batches ?? []).map((emails, index) => ({
		hour: index === 0 ? (when.value === 'later' ? 'Start' : 'Now') : `+${index} h`,
		emails,
	})),
)

const cards = computed<NumberCardProps[]>(() => {
	const data = props.preview.data
	const loading = props.preview.loading && !data
	const leftOut = Object.entries(data?.left_out ?? {}) as [SubscriberStatus, number][]
	const lastBatch = Math.max((data?.batches.length ?? 0) - 1, 0)
	return [
		{ title: 'Recipients', value: data ? data.recipients : null, deltaCaption: 'Active subscribers', loading },
		{
			title: 'Left out',
			value: data ? leftOut.reduce((sum, [, count]) => sum + count, 0) : null,
			deltaCaption: leftOut.map(([status, count]) => `${count} ${status.toLowerCase()}`).join(', ') || 'In the audience, not Active',
			loading,
		},
		{
			title: 'Finishes',
			value: data ? (lastBatch ? `In ${lastBatch} ${lastBatch === 1 ? 'hour' : 'hours'}` : 'Now') : null,
			deltaCaption: when.value === 'later' ? 'After the send starts' : 'Last batch',
			loading,
		},
	]
})

async function submit(close: () => void) {
	saving.value = true
	const saved = await props.save()
	saving.value = false
	if (!saved) return

	const status =
		when.value === 'later'
			? await scheduleCall.submit({ issue: props.issueId, scheduled_at: scheduledAt.value })
			: await sendCall.submit({ issue: props.issueId })
	if (!status) return
	toast.success(when.value === 'later' ? 'Newsletter scheduled' : 'Sending started')
	emit('sent')
	close()
}
</script>
