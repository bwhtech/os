<template>
	<PageHeader>
		<PageHeaderTitle class="min-w-0 flex-1">
			<h1 class="truncate">Dashboard</h1>
		</PageHeaderTitle>
	</PageHeader>

	<div class="space-y-4 px-3 py-5 pb-10 sm:px-5">
		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
			<NumberCard v-for="card in cards" :key="card.title" v-bind="{ ...card, ...state }" />
		</div>

		<div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
			<section :class="[CARD, 'h-80 lg:col-span-2']">
				<BarChart v-bind="{ ...growthChart, ...state }" />
			</section>
			<section :class="[CARD, 'h-80']">
				<DonutChart v-bind="{ ...statusChart, ...state }" />
			</section>
		</div>

		<section class="space-y-3 pt-2">
			<div class="flex min-w-0 items-baseline gap-2">
				<h2 class="shrink-0 text-lg font-semibold text-ink-gray-9">Last newsletter</h2>
				<RouterLink
					v-if="lastIssue"
					:to="{ name: 'Newsletter', params: { issueId: lastIssue.name } }"
					class="truncate text-base text-ink-gray-6 hover:text-ink-gray-9 hover:underline"
				>
					{{ lastIssue.subject }}, sent {{ dayjs(lastIssue.sent_at).format('D MMM YYYY') }}
				</RouterLink>
			</div>
			<p v-if="overview.data && !lastIssue" class="text-p-base text-ink-gray-5">
				No newsletter is sent yet.
			</p>
			<div v-else class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
				<NumberCard v-for="card in issueCards" :key="card.title" v-bind="{ ...card, ...state }" />
			</div>
		</section>

		<div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
			<section :class="[CARD, 'h-80']">
				<LineChart v-bind="{ ...ratesChart, ...state }" />
			</section>
			<section :class="[CARD, 'h-80']">
				<BarChart v-bind="{ ...formsChart, ...state }" />
			</section>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { PageHeader, PageHeaderTitle, dayjs, useCall } from 'frappe-ui'
import {
	BarChart,
	DonutChart,
	LineChart,
	NumberCard,
	type BarChartProps,
	type DonutChartProps,
	type LineChartProps,
	type NumberCardProps,
} from 'frappe-ui/charts'
import { lastPeriodCard } from '@/lib/activity'
import { engagementCards } from '@/lib/engagement'
import { errorMessage } from '@/lib/errors'
import type { ListOverview } from '@/types'

// Charts draw their own title and states. The card is only the surface.
const CARD = 'flex min-w-0 flex-col rounded-xl border border-outline-gray-1 bg-surface-elevation-2 px-4 py-3'

const percent = (value: number) => `${Math.round(value)}%`

const overview = useCall<ListOverview>({
	url: '/api/v2/method/bwh_os.mailing.api.get_list_overview',
	method: 'GET',
	refetch: true,
})

const state = computed(() => ({
	loading: overview.loading && !overview.data,
	error: overview.error ? errorMessage(overview.error) : null,
}))

const lastIssue = computed(() => overview.data?.last_issue ?? null)

const cards = computed<NumberCardProps[]>(() => {
	const data = overview.data
	const active = data?.by_status.find((row) => row.value === 'Active')?.count
	return [
		{ title: 'Active subscribers', value: data ? (active ?? 0) : null, deltaCaption: 'Now' },
		lastPeriodCard('New subscribers, last 30 days', data?.subscribers),
		{
			...lastPeriodCard('Unsubscribes, last 30 days', data?.unsubscribes),
			negativeIsBetter: true,
		},
		lastPeriodCard('Downloads, last 30 days', data?.downloads),
	]
})

const issueCards = computed<NumberCardProps[]>(() => [
	{ title: 'Recipients', value: lastIssue.value?.recipient_count ?? null },
	...engagementCards(lastIssue.value),
])

const growthChart = computed<BarChartProps>(() => {
	const data = overview.data
	const unsubscribes = data?.unsubscribes.weekly ?? []
	return {
		data: (data?.subscribers.weekly ?? []).map((row, index) => ({
			week: dayjs(row.week).format('D MMM'),
			New: row.count,
			Unsubscribed: unsubscribes[index]?.count ?? 0,
		})),
		x: 'week',
		y: ['New', 'Unsubscribed'],
		palette: 'categorical',
		title: 'List growth',
		subtitle: 'New subscribers and unsubscribes per week, last 12 weeks',
	}
})

const statusChart = computed<DonutChartProps>(() => ({
	data: overview.data?.by_status ?? [],
	category: 'value',
	value: 'count',
	palette: 'categorical',
	centerLabel: 'subscribers',
	title: 'Subscribers by status',
	subtitle: 'All time',
}))

const ratesChart = computed<LineChartProps>(() => ({
	data: overview.data?.issue_rates ?? [],
	x: 'subject',
	y: ['open_rate', 'click_rate'],
	yAxis: { min: 0, max: 100, format: percent },
	seriesConfig: {
		open_rate: { label: 'Open rate', showDataPoints: true },
		click_rate: { label: 'Click rate', showDataPoints: true, lineType: 'dashed' },
	},
	palette: 'categorical',
	title: 'Open and click rates',
	subtitle: 'Last 10 sent issues, oldest first',
}))

const formsChart = computed<BarChartProps>(() => ({
	data: overview.data?.by_form ?? [],
	x: 'form',
	y: ['signups', 'confirm_rate'],
	y2Axis: { min: 0, max: 100, format: percent },
	seriesConfig: {
		signups: { label: 'Signups' },
		confirm_rate: { label: 'Confirm rate', type: 'line', axis: 'y2', showDataPoints: true, showDataLabels: true },
	},
	palette: 'categorical',
	title: 'Signups by form',
	subtitle: 'All time. Only double opt-in forms have a confirm rate.',
}))
</script>
