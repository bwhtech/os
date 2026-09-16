<template>
	<div class="space-y-2">
		<div
			v-for="target in targets"
			:key="target.channel"
			class="rounded-6 border border-outline-gray-2 px-3 py-2.5"
		>
			<div class="flex items-center gap-2">
				<Avatar
					:image="channels[target.channel]?.avatar_url ?? undefined"
					:label="channels[target.channel]?.display_name ?? target.provider"
					size="sm"
				/>
				<p class="min-w-0 flex-1 truncate text-p-sm text-ink-gray-8">
					{{ channels[target.channel]?.display_name ?? target.provider }}
				</p>
				<Badge :theme="TARGET_THEMES[target.status]" :label="target.status" />
			</div>

			<a
				v-if="target.release_url"
				:href="target.release_url"
				target="_blank"
				rel="noopener"
				class="mt-2 inline-flex items-center gap-1 text-p-sm text-ink-blue-3 hover:underline"
			>
				View on {{ target.provider }}
				<span class="lucide-external-link size-3.5" aria-hidden="true" />
			</a>

			<p v-if="target.error" class="mt-2 text-p-sm text-ink-red-3">
				<span v-if="target.error_kind" class="font-medium">{{ target.error_kind }}:</span>
				{{ target.error }}
			</p>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Avatar, Badge } from 'frappe-ui'
import { TARGET_THEMES } from '@/lib/social'
import type { SocialChannel, SocialPostTarget } from '@/types'

/** What each channel made of the post: the link it got, or why it got nothing. */
defineProps<{ targets: SocialPostTarget[]; channels: Record<string, SocialChannel> }>()
</script>
