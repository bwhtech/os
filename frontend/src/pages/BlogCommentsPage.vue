<template>
	<PageHeader>
		<PageHeaderTitle class="min-w-0 flex-1">
			<h1 class="truncate">Comments</h1>
		</PageHeaderTitle>
	</PageHeader>

	<div class="px-3 py-5 pb-10 sm:px-5">
		<LoadingText v-if="!comments.data && !error" :lines="4" />

		<ErrorMessage v-else-if="error" :message="errorMessage(error)" />

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
				@set-hidden="(hidden) => hide(selectedIds, hidden)"
				@delete="confirmDelete(selectedIds)"
				@clear="selection = []"
			/>
			<p v-if="truncated" class="mt-2 text-sm text-ink-amber-7">
				Showing the latest {{ COMMENT_LIMIT.toLocaleString() }} comments
			</p>

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
					@delete="(comment) => confirmDelete([Number(comment.name)], describe(comment, group.post))"
				/>
			</div>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
	ErrorMessage,
	LoadingText,
	PageHeader,
	PageHeaderTitle,
	dayjs,
	debounce,
	dialog,
	toast,
	useCall,
	useList,
} from 'frappe-ui'
import CommentGroup from '@/components/blog/CommentGroup.vue'
import CommentToolbar from '@/components/blog/CommentToolbar.vue'
import { filterGroups, groupByPost, type CommentStatus } from '@/lib/blogComments'
import { errorMessage } from '@/lib/errors'
import { onListUpdate } from '@/lib/socket'
import type { BlogComment, BlogPost, BlogPostRow } from '@/types'

/** The page loads all comments at once. Above this, it shows only the newest. */
const COMMENT_LIMIT = 2000
/** Groups with a comment newer than this start open. */
const RECENT_DAYS = 7
const EXCERPT_LENGTH = 120

const route = useRoute()

// One more row than the limit tells us that there are more comments.
const comments = useList<BlogComment>({
	doctype: 'BWH Blog Comment',
	fields: ['name', 'post', 'commenter_name', 'email', 'body', 'hidden', 'creation'],
	orderBy: 'creation desc',
	limit: COMMENT_LIMIT + 1,
})

const postRows = useList<BlogPostRow>({
	doctype: 'BWH Blog Post',
	fields: ['name', 'title', 'likes'],
	limit: 0,
})

// A new comment from the blog, a like, or a change in another tab. A bulk action sends one
// event for each comment, so wait for the burst to end.
const reloadAll = debounce(() => {
	comments.reload()
	postRows.reload()
}, 300)
onListUpdate(['BWH Blog Comment', 'BWH Blog Post'], reloadAll)

const error = computed(() => comments.error ?? postRows.error)
const truncated = computed(() => (comments.data?.length ?? 0) > COMMENT_LIMIT)
const posts = computed(() =>
	groupByPost((comments.data ?? []).slice(0, COMMENT_LIMIT), postRows.data ?? []),
)

const status = ref<CommentStatus>('')
const search = ref('')
const groups = computed(() => filterGroups(posts.value, status.value, search.value))

const summary = computed(() => {
	const count = groups.value.reduce((total, group) => total + group.comments.length, 0)
	return `${plural(count, 'comment')} on ${plural(groups.value.length, 'post')}`
})

// Comment names, as strings, across all groups.
const selection = ref<string[]>([])
const selectedIds = computed(() => selection.value.map(Number))
// A row that a filter hides must not stay selected out of sight.
watch([status, search], () => (selection.value = []))

const setHidden = useCall<number, { ids: number[]; hidden: boolean }>({
	url: '/api/v2/method/bwh_os.blog.api.set_hidden',
	method: 'POST',
	immediate: false,
})

const deleteComments = useCall<number, { ids: number[] }>({
	url: '/api/v2/method/bwh_os.blog.api.delete_comments',
	method: 'POST',
	immediate: false,
})

// The lists reload from the realtime update after each action.
async function hide(ids: number[], hidden: boolean) {
	try {
		await setHidden.submit({ ids, hidden })
		toast.success(`${plural(ids.length, 'comment')} ${hidden ? 'hidden' : 'shown'} on the blog`)
		selection.value = []
	} catch (error) {
		toast.error(errorMessage(error as Error))
	}
}

/** One comment shows what goes. Many show only the count. */
function confirmDelete(ids: number[], detail?: string) {
	const what = detail ?? `The ${plural(ids.length, 'selected comment')} go from OS and from the blog.`
	dialog.danger({
		title: ids.length === 1 ? 'Delete comment?' : `Delete ${ids.length} comments?`,
		message: `${what} You cannot undo this.`,
		onConfirm: async () => {
			// A failed delete throws here, and the dialog shows the error.
			await deleteComments.submit({ ids })
			toast.success(`${plural(ids.length, 'comment')} deleted`)
			selection.value = []
		},
	})
}

function describe(comment: BlogComment, post: BlogPost) {
	const body =
		comment.body.length > EXCERPT_LENGTH ? `${comment.body.slice(0, EXCERPT_LENGTH)}…` : comment.body
	return `${comment.commenter_name} on "${post.title}": "${body}".`
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
	return dayjs(post.comments[0]?.creation).isAfter(dayjs().subtract(RECENT_DAYS, 'day'))
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
