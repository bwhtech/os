<template>
	<PageHeader>
		<PageHeaderTitle class="min-w-0 flex-1">
			<h1 class="truncate">Comments</h1>
		</PageHeaderTitle>
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

		<div v-else-if="!posts.length" class="flex flex-col items-center justify-center gap-3 py-16 text-center">
			<div class="rounded-full bg-surface-gray-2 p-3 text-ink-gray-5">
				<span class="lucide-message-square size-6" aria-hidden="true" />
			</div>
			<p class="text-base text-ink-gray-7">No comments yet</p>
			<p class="text-sm text-ink-gray-5">Comments from bwh.tech/blog show here.</p>
		</div>

		<template v-else>
			<CommentToolbar
				v-model:status="status"
				v-model:search="search"
				:selected-count="selection.length"
				:summary="summary"
				:busy="setHidden.loading"
				@set-hidden="(hidden) => hide(selection.map(Number), hidden)"
				@clear="selection = []"
			/>
			<p v-if="truncated" class="mt-2 text-sm text-ink-amber-7">Showing the latest 2,000 comments</p>

			<p v-if="!groups.length" class="py-10 text-center text-p-base text-ink-gray-5">
				No comments match the filters
			</p>
			<div class="mt-4 space-y-4">
				<CommentGroup
					v-for="group in groups"
					:key="group.post.post_id"
					v-model:selection="selection"
					:post="group.post"
					:comments="group.comments"
					:open="groupOpen(group.post)"
					@toggle="toggleGroup(group.post)"
					@set-hidden="hide"
				/>
			</div>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
	Button,
	ErrorMessage,
	LoadingText,
	PageHeader,
	PageHeaderTitle,
	dayjs,
	toast,
	useCall,
} from 'frappe-ui'
import CommentGroup from '@/components/blog/CommentGroup.vue'
import CommentToolbar from '@/components/blog/CommentToolbar.vue'
import { filterGroups, type CommentStatus } from '@/lib/blogComments'
import { errorMessage } from '@/lib/errors'
import type { BlogCommentFeed, BlogPost } from '@/types'

/** Groups with a comment newer than this start open. */
const RECENT_DAYS = 7

const route = useRoute()

const feed = useCall<BlogCommentFeed>({
	url: '/api/v2/method/bwh_os.blog.api.get_comments',
	method: 'GET',
	refetch: true,
})

const posts = computed(() => feed.data?.posts ?? [])
const truncated = computed(() => feed.data?.truncated ?? false)

const status = ref<CommentStatus>('')
const search = ref('')
const groups = computed(() => filterGroups(posts.value, status.value, search.value))

const summary = computed(() => {
	const comments = groups.value.reduce((total, group) => total + group.comments.length, 0)
	return `${plural(comments, 'comment')} on ${plural(groups.value.length, 'post')}`
})

// Comment ids, as strings, across all groups.
const selection = ref<string[]>([])
// A row that a filter hides must not stay selected out of sight.
watch([status, search], () => (selection.value = []))

const setHidden = useCall<number, { ids: number[]; hidden: boolean }>({
	url: '/api/v2/method/bwh_os.blog.api.set_hidden',
	method: 'POST',
	immediate: false,
})

async function hide(ids: number[], hidden: boolean) {
	try {
		await setHidden.submit({ ids, hidden })
		toast.success(`${plural(ids.length, 'comment')} ${hidden ? 'hidden' : 'shown'} on the blog`)
		selection.value = []
		await feed.reload()
	} catch (error) {
		toast.error(errorMessage(error as Error))
	}
}

// Your toggles override the default open state of a group.
const openState = reactive<Record<string, boolean>>({})

function groupOpen(post: BlogPost) {
	// While searching, every group with a match is open.
	if (search.value.trim()) return true
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
