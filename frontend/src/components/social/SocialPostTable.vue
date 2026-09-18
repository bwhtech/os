<template>
	<!-- Rows are links, so the hover surface bleeds into the gutter. -->
	<div class="-mx-3 overflow-x-auto">
		<List
			class="min-w-[42rem] list-row-px-3"
			:columns="['minmax(12rem,1fr)', '10rem', '8rem', '9rem']"
			:row-height="44"
		>
			<ListHeader>
				<ListHeaderCell>Post</ListHeaderCell>
				<ListHeaderCell>Channels</ListHeaderCell>
				<ListHeaderCell>Status</ListHeaderCell>
				<ListHeaderCell class="justify-end">When</ListHeaderCell>
			</ListHeader>
			<ListRows :items="posts" row-key="name">
				<template #default="{ item, value }">
					<ListRow :value="value" :route="postRoute(item)">
						<ListCell>
							<span
								class="truncate text-base"
								:class="item.title ? 'text-ink-gray-8' : 'text-ink-gray-4'"
							>
								{{ item.title || 'Untitled post' }}
							</span>
						</ListCell>
						<ListCell>
							<span class="flex items-center gap-1.5">
								<span
									v-for="target in item.targets"
									:key="target.channel"
									class="relative inline-flex"
								>
									<Avatar
										:image="target.avatar_url ?? undefined"
										:label="target.display_name ?? target.provider"
										size="sm"
									/>
									<span
										:class="[
											'absolute -bottom-0.5 -right-0.5 size-2 rounded-full ring-2 ring-surface-white',
											dot(target.status),
										]"
										:title="`${target.provider}: ${target.status}`"
									/>
								</span>
								<span v-if="!item.targets.length" class="text-sm text-ink-gray-4">—</span>
							</span>
						</ListCell>
						<ListCell>
							<Badge :theme="POST_STATUS_THEMES[item.status]" :label="item.status" />
						</ListCell>
						<ListCell class="justify-end">
							<span class="text-sm text-ink-gray-5">{{ when(item) }}</span>
						</ListCell>
					</ListRow>
				</template>
			</ListRows>
		</List>
	</div>
</template>

<script setup lang="ts">
import { Avatar, Badge, dayjs } from 'frappe-ui'
import { List, ListCell, ListHeader, ListHeaderCell, ListRow, ListRows } from 'frappe-ui/list'
import { POST_STATUS_THEMES, postRoute } from '@/lib/social'
import type { SocialPostRow, SocialTargetStatus } from '@/types'

defineProps<{ posts: SocialPostRow[] }>()

const DOTS: Record<SocialTargetStatus, string> = {
	Pending: 'bg-surface-gray-4',
	Publishing: 'bg-surface-amber-7',
	Published: 'bg-surface-green-7',
	Failed: 'bg-surface-red-6',
}

function dot(status: SocialTargetStatus): string {
	return DOTS[status] ?? DOTS.Pending
}

/** When it goes out, or when it went. A draft has neither, so it shows its last edit. */
function when(post: SocialPostRow): string {
	if (post.published_at) return dayjs(post.published_at).fromNow()
	if (post.scheduled_at) return dayjs(post.scheduled_at).format('D MMM, h:mm A')
	return `Edited ${dayjs(post.modified).fromNow()}`
}
</script>
