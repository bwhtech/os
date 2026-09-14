<template>
	<!-- Feed mode: avatar, content, trailing cell. -->
	<ListCell class="self-start pt-1">
		<Avatar :label="comment.name" size="lg" />
	</ListCell>
	<ListCell class="py-1">
		<!-- ListCell centers its items, so the content needs its own column. -->
		<div class="flex w-full min-w-0 flex-col items-start gap-1" :class="comment.hidden && 'opacity-60'">
			<div class="flex min-w-0 max-w-full items-baseline gap-2">
				<span class="truncate text-base-medium text-ink-gray-8">{{ comment.name }}</span>
				<span class="truncate text-sm text-ink-gray-5">{{ comment.email }}</span>
				<Tooltip :text="postedAt.format('D MMM YYYY, h:mm A')">
					<span class="shrink-0 text-sm text-ink-gray-5">{{ postedAt.fromNow() }}</span>
				</Tooltip>
			</div>
			<!-- Plain text, as on the blog. Never v-html. -->
			<p
				ref="body"
				class="whitespace-pre-line break-words text-p-base text-ink-gray-7"
				:class="!expanded && 'line-clamp-3'"
			>
				{{ comment.body }}
			</p>
			<Button
				v-if="clamped || expanded"
				variant="ghost"
				size="sm"
				class="-ml-2"
				:label="expanded ? 'Show less' : 'Show more'"
				@click="expanded = !expanded"
			/>
		</div>
	</ListCell>
	<ListCell class="self-start pt-1">
		<Badge v-if="comment.hidden" label="Hidden" theme="gray" variant="subtle" />
	</ListCell>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, useTemplateRef } from 'vue'
import { Avatar, Badge, Button, Tooltip, dayjs } from 'frappe-ui'
import { ListCell } from 'frappe-ui/list'
import type { BlogComment } from '@/types'

const props = defineProps<{ comment: BlogComment }>()

const expanded = ref(false)
const clamped = ref(false)
const body = useTemplateRef<HTMLParagraphElement>('body')
const postedAt = computed(() => dayjs.unix(props.comment.created_at))

// Show the toggle only when the clamp cuts text. The width, and so the cut, changes on resize.
const observer = new ResizeObserver(() => {
	if (body.value && !expanded.value) clamped.value = body.value.scrollHeight > body.value.clientHeight
})
onMounted(() => body.value && observer.observe(body.value))
onBeforeUnmount(() => observer.disconnect())
</script>
