<template>
	<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
		<NumberCard
			v-for="card in cards"
			:key="card.title"
			v-bind="card"
			:loading="activity.loading && !activity.data"
			:error="activity.error ? errorMessage(activity.error) : null"
		/>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useCall } from 'frappe-ui'
import { NumberCard } from 'frappe-ui/charts'
import { lastPeriodCard, totalCard } from '@/lib/activity'
import { errorMessage } from '@/lib/errors'
import type { Activity } from '@/types'

const props = defineProps<{
	/** Whitelisted method that returns an `Activity` */
	method: string
	params: Record<string, string>
	/** Plural noun for what is counted, e.g. "Downloads" */
	label: string
}>()

const activity = useCall<Activity, Record<string, string>>({
	url: `/api/v2/method/${props.method}`,
	method: 'GET',
	params: () => props.params,
	refetch: true,
})

const cards = computed(() => [
	totalCard(props.label, activity.data),
	lastPeriodCard(`${props.label}, last 30 days`, activity.data),
])
</script>
