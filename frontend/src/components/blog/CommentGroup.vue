<template>
	<section :id="`post-${post.post_id}`" class="scroll-mt-4">
		<!-- The group header follows the Tasks recipe in frappe-ui. -->
		<div class="group flex items-center rounded-sm bg-surface-sidebar transition hover:bg-surface-gray-2">
			<button
				class="flex min-w-0 flex-1 items-baseline px-2.5 py-2 text-left text-base"
				:aria-expanded="open"
				@click="emit('toggle')"
			>
				<span class="truncate font-medium text-ink-gray-8">{{ post.title }}</span>
				<span class="ml-2 shrink-0 text-sm text-ink-gray-5">{{ counts }}</span>
				<span class="ml-auto hidden shrink-0 pl-2 text-sm text-ink-gray-5 group-hover:inline">
					{{ open ? 'Collapse' : 'Expand' }}
				</span>
			</button>
			<Tooltip text="Open the post">
				<Button
					variant="ghost"
					icon="lucide-external-link"
					label="Open the post"
					class="mr-1"
					:link="post.url"
				/>
			</Tooltip>
		</div>

		<List v-if="open" class="mt-1">
			<ListRow v-for="comment in post.comments" :key="comment.id" :value="String(comment.id)">
				<CommentRow :comment="comment" />
			</ListRow>
		</List>
	</section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button, Tooltip } from 'frappe-ui'
import { List, ListRow } from 'frappe-ui/list'
import CommentRow from '@/components/blog/CommentRow.vue'
import type { BlogPost } from '@/types'

/** One post and its comments on the Comments page. */
const props = defineProps<{ post: BlogPost; open: boolean }>()
const emit = defineEmits<{ toggle: [] }>()

const counts = computed(() => {
	const total = props.post.comments.length
	const hidden = props.post.comments.filter((comment) => comment.hidden).length
	const parts = [`${total} ${total === 1 ? 'comment' : 'comments'}`]
	if (hidden) parts.push(`${hidden} hidden`)
	parts.push(`${props.post.likes} ${props.post.likes === 1 ? 'like' : 'likes'}`)
	return parts.join(' · ')
})
</script>
