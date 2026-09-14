<template>
	<!-- Feed mode: avatar, content, trailing cell. -->
	<ListCell class="self-start pt-1">
		<Avatar :label="comment.commenter_name" size="lg" />
	</ListCell>
	<ListCell class="py-1">
		<!-- ListCell centers its items, so the content needs its own column. -->
		<div class="flex w-full min-w-0 flex-col items-start gap-1" :class="{ 'opacity-60': comment.hidden }">
			<div class="flex min-w-0 max-w-full items-baseline gap-2">
				<span class="truncate text-base-medium text-ink-gray-8">{{ comment.commenter_name }}</span>
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
				@click.stop="expanded = !expanded"
			/>
		</div>
	</ListCell>
	<ListCell class="gap-1 self-start">
		<Badge v-if="comment.hidden" label="Hidden" theme="gray" variant="subtle" />
		<!-- A selectable row toggles on click. The menu must not. -->
		<span @click.stop>
			<Dropdown :options="menu" placement="right">
				<Button variant="ghost" icon="lucide-ellipsis" label="Comment actions" />
			</Dropdown>
		</span>
	</ListCell>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, useTemplateRef } from 'vue'
import { Avatar, Badge, Button, Dropdown, Tooltip, dayjs, type DropdownOptions } from 'frappe-ui'
import { ListCell } from 'frappe-ui/list'
import type { BlogComment } from '@/types'

const props = defineProps<{ comment: BlogComment }>()
const emit = defineEmits<{ 'set-hidden': [hidden: boolean]; delete: [] }>()

const expanded = ref(false)
const clamped = ref(false)
const body = useTemplateRef<HTMLParagraphElement>('body')
const postedAt = computed(() => dayjs(props.comment.creation))

const menu = computed<DropdownOptions>(() => [
	props.comment.hidden
		? { label: 'Unhide', icon: 'lucide-eye', onClick: () => emit('set-hidden', false) }
		: { label: 'Hide', icon: 'lucide-eye-off', onClick: () => emit('set-hidden', true) },
	{ label: 'Delete', icon: 'lucide-trash-2', theme: 'red', onClick: () => emit('delete') },
])

// Show the toggle only when the clamp cuts text. The width, and so the cut, changes on resize.
const observer = new ResizeObserver(() => {
	if (body.value && !expanded.value) clamped.value = body.value.scrollHeight > body.value.clientHeight
})
onMounted(() => body.value && observer.observe(body.value))
onBeforeUnmount(() => observer.disconnect())
</script>
