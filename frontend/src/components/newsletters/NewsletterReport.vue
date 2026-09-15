<template>
	<div ref="root" class="space-y-4">
		<p class="text-p-base text-ink-gray-6">
			<template v-if="issue.status === 'Sending'">
				Sending since {{ formatTime(issue.sent_at) }}. The counts update every 2 minutes.
			</template>
			<template v-else-if="issue.completed_at">
				Sent {{ formatTime(issue.sent_at) }}. The last email left {{ formatTime(issue.completed_at) }}.
			</template>
		</p>

		<div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
			<NumberCard v-for="card in cards" :key="card.title" v-bind="card" />
		</div>

		<NewsletterEngagement :issue="issue" :refresh-key="refreshKey" />

		<section class="h-72 rounded-7 border border-outline-gray-1 px-4 py-3">
			<BarChart
				:data="batchRows"
				x="hour"
				:y="STATUSES"
				stacked
				:palette="statusColors"
				title="Emails per hourly batch"
				:subtitle="`At most ${issue.hourly_limit} an hour`"
				:loading="progress.loading && !progress.data"
				:error="progress.error ? errorMessage(progress.error) : null"
			/>
		</section>

		<DeliveryList :issue-id="issue.name" :refresh-key="refreshKey" />
	</div>
</template>

<script setup lang="ts">
import { computed, onScopeDispose, ref, watch } from 'vue'
import { dayjs, useCall } from 'frappe-ui'
import { BarChart, NumberCard, useChartTokens, type NumberCardProps } from 'frappe-ui/charts'
import DeliveryList from '@/components/newsletters/DeliveryList.vue'
import NewsletterEngagement from '@/components/newsletters/NewsletterEngagement.vue'
import { errorMessage } from '@/lib/errors'
import type { DeliveryStatus, NewsletterIssue, NewsletterProgress } from '@/types'

const props = defineProps<{ issue: NewsletterIssue }>()
const emit = defineEmits<{ refresh: [] }>()

const STATUSES: DeliveryStatus[] = ['Sent', 'Queued', 'Failed', 'Skipped']
/** Slots of the categorical ramp, in STATUSES order: emerald, light blue, crimson, light amber. */
const STATUS_SLOTS = [2, 1, 8, 7]
// The send job makes the rows within seconds. The sync job moves them to Sent every 2 minutes.
const POLL_MS = 15_000

const refreshKey = ref(0)
const root = ref<HTMLElement>()
const { tokens } = useChartTokens(root)

const statusColors = computed(() => STATUS_SLOTS.map((slot) => tokens.value.categorical[slot]))

const progress = useCall<NewsletterProgress, { issue: string }>({
	url: '/api/v2/method/bwh_os.mailing.api.get_newsletter_progress',
	method: 'GET',
	params: () => ({ issue: props.issue.name }),
})

let timer: ReturnType<typeof setInterval> | undefined

watch(
	() => props.issue.status,
	(status) => {
		clearInterval(timer)
		if (status !== 'Sending') return
		timer = setInterval(() => {
			progress.reload()
			refreshKey.value++
			emit('refresh')
		}, POLL_MS)
	},
	{ immediate: true },
)

onScopeDispose(() => clearInterval(timer))

const batchRows = computed(() =>
	(progress.data?.batches ?? []).map((batch) => ({
		...batch,
		hour: batch.sends_at ? dayjs(batch.sends_at).format('D MMM, h a') : `Hour ${batch.batch + 1}`,
	})),
)

const cards = computed<NumberCardProps[]>(() => {
	// The progress call reloads with the poll, so it is newer than the issue counts.
	const counts = progress.data?.counts
	const sent = counts?.Sent ?? props.issue.sent_count
	const failed = counts?.Failed ?? props.issue.failed_count
	const skipped = counts?.Skipped ?? props.issue.skipped_count
	const recipients = counts ? Object.values(counts).reduce((sum, count) => sum + count, 0) : props.issue.recipient_count
	return [
		{ title: 'Recipients', value: recipients, deltaCaption: 'When the send started' },
		{ title: 'Sent', value: sent, deltaCaption: share(sent, recipients) },
		{ title: 'Failed', value: failed, deltaCaption: share(failed, recipients) },
		{ title: 'Skipped', value: skipped, deltaCaption: 'Not Active when queued' },
	]
})

function share(count: number, total: number) {
	if (!total) return ''
	return `${Math.round((count / total) * 100)}% of recipients`
}

function formatTime(value: string | null) {
	return value ? dayjs(value).format('D MMM YYYY, h:mm a') : ''
}
</script>
