<template>
	<PageHeader>
		<PageHeaderTitle class="min-w-0 flex-1">
			<h1 class="truncate">Comments</h1>
		</PageHeaderTitle>
		<Tooltip v-if="dbHost" text="The Turso database that this page reads and changes">
			<Badge variant="outline" theme="gray" :label="dbHost">
				<template #prefix>
					<span class="lucide-database size-3" aria-hidden="true" />
				</template>
			</Badge>
		</Tooltip>
		<Button
			variant="ghost"
			icon-left="lucide-refresh-cw"
			label="Refresh"
			:loading="feed.loading"
			@click="feed.reload()"
		/>
	</PageHeader>

	<div class="px-3 py-5 pb-10 sm:px-5">
		<LoadingText v-if="feed.loading && !feed.data" :lines="4" />

		<div v-else-if="feed.error" class="flex flex-col items-start gap-3">
			<ErrorMessage :message="errorMessage(feed.error)" />
			<Button label="Retry" icon-left="lucide-rotate-cw" @click="feed.reload()" />
		</div>

		<div v-else-if="emptyState" class="flex flex-col items-center justify-center gap-3 py-16 text-center">
			<div class="rounded-full bg-surface-gray-2 p-3 text-ink-gray-5">
				<span :class="[emptyState.icon, 'size-6']" aria-hidden="true" />
			</div>
			<p class="text-base text-ink-gray-7">{{ emptyState.title }}</p>
			<p class="text-sm text-ink-gray-5">{{ emptyState.description }}</p>
			<Button
				v-if="!configured"
				variant="solid"
				theme="gray"
				icon-left="lucide-settings"
				label="Open Blog settings"
				class="mt-2"
				@click="openSettings('blog-comments')"
			/>
		</div>

		<template v-else>
			<div class="flex flex-wrap items-center gap-2">
				<span class="text-sm text-ink-gray-5">{{ summary }}</span>
				<span v-if="truncated" class="text-sm text-ink-amber-7">
					Showing the latest 2,000 comments
				</span>
			</div>

			<div class="mt-4 space-y-4">
				<CommentGroup
					v-for="post in posts"
					:key="post.post_id"
					:post="post"
					:open="groupOpen(post)"
					@toggle="toggleGroup(post)"
				/>
			</div>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, nextTick, reactive, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
	Badge,
	Button,
	ErrorMessage,
	LoadingText,
	PageHeader,
	PageHeaderTitle,
	Tooltip,
	dayjs,
	useCall,
} from 'frappe-ui'
import CommentGroup from '@/components/blog/CommentGroup.vue'
import { useSettingsDialog } from '@/composables/useSettingsDialog'
import { errorMessage } from '@/lib/errors'
import type { BlogCommentFeed, BlogPost } from '@/types'

/** Groups with a comment newer than this start open. */
const RECENT_DAYS = 7

const route = useRoute()
const { openSettings } = useSettingsDialog()

const feed = useCall<BlogCommentFeed>({
	url: '/api/v2/method/bwh_os.blog.api.get_comments',
	method: 'GET',
	refetch: true,
})

const configured = computed(() => feed.data?.configured ?? false)
const loaded = computed(() => (feed.data?.configured ? feed.data : null))
const posts = computed(() => loaded.value?.posts ?? [])
const dbHost = computed(() => loaded.value?.db_host ?? '')
const truncated = computed(() => loaded.value?.truncated ?? false)

const summary = computed(() => {
	const comments = posts.value.reduce((total, post) => total + post.comments.length, 0)
	return `${plural(comments, 'comment')} on ${plural(posts.value.length, 'post')}`
})

const emptyState = computed(() => {
	if (!feed.data) return null
	if (!configured.value) {
		return {
			icon: 'lucide-database',
			title: 'Connect the blog database',
			description: 'Add the Turso URL and token of the blog to see its comments.',
		}
	}
	if (!posts.value.length) {
		return {
			icon: 'lucide-message-square',
			title: 'No comments yet',
			description: 'Comments from bwh.tech/blog show here.',
		}
	}
	return null
})

// Your toggles override the default open state of a group.
const openState = reactive<Record<string, boolean>>({})

function groupOpen(post: BlogPost) {
	return openState[post.post_id] ?? defaultOpen(post)
}

function toggleGroup(post: BlogPost) {
	openState[post.post_id] = !groupOpen(post)
}

function defaultOpen(post: BlogPost) {
	if (route.query.post === post.post_id) return true
	const newest = post.comments[0]?.created_at ?? 0
	return dayjs.unix(newest).isAfter(dayjs().subtract(RECENT_DAYS, 'day'))
}

// A link to one post, for example from the new comment email, scrolls to its group.
watch(
	posts,
	async (value) => {
		const postId = route.query.post
		if (!postId || !value.some((post) => post.post_id === postId)) return
		await nextTick()
		document.getElementById(`post-${postId}`)?.scrollIntoView({ block: 'start' })
	},
	{ once: true },
)

function plural(count: number, word: string) {
	return `${count} ${word}${count === 1 ? '' : 's'}`
}
</script>
