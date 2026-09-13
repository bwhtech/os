<template>
	<div class="space-y-4">
		<div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
			<NumberCard v-for="card in cards" :key="card.title" v-bind="card" />
		</div>

		<div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
			<section class="h-72 rounded-xl border border-outline-gray-1 px-4 py-3">
				<FunnelChart
					:data="report.data?.funnel ?? []"
					category="stage"
					value="count"
					title="From recipients to clicks"
					:loading="loading"
					:error="error"
				/>
			</section>

			<section class="h-72 rounded-xl border border-outline-gray-1 px-4 py-3">
				<AreaChart
					:data="hourlyRows"
					x="hour"
					:y="['Open', 'Click']"
					:series-config="{ Open: { label: 'Opens' }, Click: { label: 'Clicks' } }"
					title="Opens and clicks per hour"
					subtitle="First 72 hours of the send"
					:empty="!hasEvents"
					:loading="loading"
					:error="error"
				/>
			</section>
		</div>

		<section class="h-72 rounded-xl border border-outline-gray-1 px-4 py-3">
			<BarChart
				:data="linkRows"
				x="link"
				y="clicks"
				horizontal
				:series-config="{ clicks: { label: 'Clicks' } }"
				title="Top links"
				subtitle="Clicks on each link in the email"
				:empty="!linkRows.length"
				:loading="loading"
				:error="error"
			/>
		</section>

		<p class="text-p-sm text-ink-gray-5">
			Apple Mail loads images for its readers, so the open rate is higher than the real rate.
		</p>
	</div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { dayjs, useCall } from 'frappe-ui'
import { AreaChart, BarChart, FunnelChart, NumberCard, type NumberCardProps } from 'frappe-ui/charts'
import { errorMessage } from '@/lib/errors'
import type { NewsletterEngagement, NewsletterIssue } from '@/types'

const props = defineProps<{ issue: NewsletterIssue; refreshKey: number }>()

const MIN_HOURS = 12

const report = useCall<NewsletterEngagement, { issue: string }>({
	url: '/api/v2/method/bwh_os.mailing.api.get_newsletter_engagement',
	method: 'GET',
	params: () => ({ issue: props.issue.name }),
})

watch(
	() => props.refreshKey,
	() => report.reload(),
)

const loading = computed(() => report.loading && !report.data)
const error = computed(() => (report.error ? errorMessage(report.error) : null))

/** Hours that have passed, so a new send does not show three empty days. An area needs a few points to draw. */
const hourlyRows = computed(() => {
	const elapsed = props.issue.sent_at ? dayjs().diff(dayjs(props.issue.sent_at), 'hour') + 1 : 0
	return (report.data?.hourly ?? []).slice(0, Math.max(elapsed, MIN_HOURS)).map((row) => ({
		...row,
		hour: `+${row.hour} h`,
	}))
})

const hasEvents = computed(() => hourlyRows.value.some((row) => row.Open || row.Click))

const linkRows = computed(() =>
	(report.data?.top_links ?? []).map((link) => ({ link: shortUrl(link.url), clicks: link.clicks })),
)

const cards = computed<NumberCardProps[]>(() => {
	const data = report.data
	const previous = data?.previous
	const caption = previous ? `vs ${previous.subject}` : 'No earlier issue'
	return [
		{
			title: 'Open rate',
			value: data?.rates.open_rate ?? null,
			suffix: '%',
			...change(data?.rates.open_rate, previous?.open_rate, ' pts'),
			deltaCaption: caption,
			loading: loading.value,
		},
		{
			title: 'Click rate',
			value: data?.rates.click_rate ?? null,
			suffix: '%',
			...change(data?.rates.click_rate, previous?.click_rate, ' pts'),
			deltaCaption: caption,
			loading: loading.value,
		},
		{
			title: 'Unsubscribes',
			value: data?.rates.unsubscribes ?? null,
			...change(data?.rates.unsubscribes, previous?.unsubscribes),
			negativeIsBetter: true,
			deltaCaption: caption,
			loading: loading.value,
		},
	]
})

function change(current: number | null | undefined, previous: number | null | undefined, suffix = '') {
	if (current == null || previous == null) return {}
	return { delta: Math.round((current - previous) * 10) / 10, deltaSuffix: suffix }
}

function shortUrl(url: string) {
	try {
		const parsed = new URL(url)
		return `${parsed.hostname.replace(/^www\./, '')}${parsed.pathname === '/' ? '' : parsed.pathname}`
	} catch {
		return url
	}
}
</script>
