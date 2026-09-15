<template>
	<AppPageHeader title="Blog" />

	<div class="space-y-4 px-3 py-5 pb-10 sm:px-5">
		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
			<NumberCard v-for="card in cards" :key="card.title" v-bind="{ ...card, ...state }" />
		</div>

		<section :class="[CARD, 'h-80']">
			<BarChart v-bind="{ ...weeklyChart, ...state }" />
		</section>

		<div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
			<section :class="[CARD, 'h-96']">
				<BarChart v-bind="{ ...commentsChart, ...state }" @select="openPost" />
			</section>
			<section :class="[CARD, 'h-96']">
				<BarChart v-bind="{ ...likesChart, ...state }" @select="openPost" />
			</section>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { dayjs, debounce, useCall } from 'frappe-ui'
import AppPageHeader from '@/components/shell/AppPageHeader.vue'
import {
	BarChart,
	NumberCard,
	type BarChartProps,
	type ChartDatapointEvent,
	type NumberCardProps,
} from 'frappe-ui/charts'
import { lastPeriodCard, totalCard } from '@/lib/activity'
import { errorMessage } from '@/lib/errors'
import { onListUpdate } from '@/lib/socket'
import type { BlogOverview, BlogTopPost } from '@/types'

// Charts draw their own title and states. The card is only the surface.
const CARD = 'flex min-w-0 flex-col rounded-7 border border-outline-gray-1 bg-surface-elevation-2 px-4 py-3'

const overview = useCall<BlogOverview>({
	url: '/api/v2/method/bwh_os.blog.api.get_overview',
	method: 'GET',
	refetch: true,
})

// New comments and likes arrive from the blog while the page is open.
onListUpdate(
	['BWH Blog Comment', 'BWH Blog Post'],
	debounce(() => overview.reload(), 300),
)

const state = computed(() => ({
	loading: overview.loading && !overview.data,
	error: overview.error ? errorMessage(overview.error) : null,
}))

const cards = computed<NumberCardProps[]>(() => {
	const data = overview.data
	return [
		lastPeriodCard('Comments, last 30 days', data?.comments),
		totalCard('Comments', data?.comments),
		{ title: 'Hidden comments', value: data?.hidden ?? null, deltaCaption: 'All time' },
		{ title: 'Likes', value: data?.likes ?? null, deltaCaption: 'All time' },
	]
})

const weeklyChart = computed<BarChartProps>(() => ({
	data: (overview.data?.comments.weekly ?? []).map((row) => ({
		week: dayjs(row.week).format('D MMM'),
		Comments: row.count,
	})),
	x: 'week',
	y: ['Comments'],
	palette: 'categorical',
	title: 'Comments per week',
	subtitle: 'Last 12 weeks, hidden comments included',
}))

const router = useRouter()

const commentsChart = computed(() =>
	topPostsChart(overview.data?.top_by_comments, 'Comments', 'Most comments', 'Hidden comments included. Click a bar to see the comments.'),
)
const likesChart = computed(() =>
	topPostsChart(overview.data?.top_by_likes, 'Likes', 'Most likes', 'Click a bar to see the comments.'),
)

/** A horizontal bar for each post, most first. The server sends the posts sorted. */
function topPostsChart(posts: BlogTopPost[] | undefined, measure: string, title: string, subtitle: string): BarChartProps {
	return {
		data: (posts ?? []).map((post) => ({
			post: post.title || post.post_id,
			post_id: post.post_id,
			[measure]: post.count,
		})),
		x: 'post',
		y: [measure],
		horizontal: true,
		palette: 'categorical',
		title,
		subtitle,
	}
}

function openPost(event: ChartDatapointEvent) {
	const postId = event.row?.post_id
	if (postId) router.push({ name: 'Blog Comments', query: { post: String(postId) } })
}
</script>
