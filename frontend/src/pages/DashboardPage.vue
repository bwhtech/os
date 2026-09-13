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
			<section :class="[CARD, 'h-72 lg:col-span-3']">
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
	NumberCard,
	type BarChartProps,
	type DonutChartProps,
	type NumberCardProps,
} from 'frappe-ui/charts'
import { lastPeriodCard } from '@/lib/activity'
import { errorMessage } from '@/lib/errors'
import type { ListOverview } from '@/types'

// Charts draw their own title and states. The card is only the surface.
const CARD = 'flex min-w-0 flex-col rounded-xl border border-outline-gray-1 bg-surface-elevation-2 px-4 py-3'

const overview = useCall<ListOverview>({
	url: '/api/v2/method/bwh_os.mailing.api.get_list_overview',
	method: 'GET',
	refetch: true,
})

const state = computed(() => ({
	loading: overview.loading && !overview.data,
	error: overview.error ? errorMessage(overview.error) : null,
}))

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

const formsChart = computed<BarChartProps>(() => ({
	data: overview.data?.by_form ?? [],
	x: 'form',
	y: 'count',
	horizontal: true,
	seriesConfig: { count: { label: 'Subscribers', showDataLabels: true } },
	title: 'Subscribers by signup form',
	subtitle: 'All time. People added by hand or imported have no form.',
}))
</script>
