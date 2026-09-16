<template>
	<div class="space-y-2">
		<div class="rounded-6 border border-outline-gray-2 bg-surface-white p-4">
			<div class="flex items-center gap-2">
				<Avatar :image="channel?.avatar_url ?? undefined" :label="name" size="lg" />
				<div class="min-w-0">
					<p class="truncate text-p-sm font-medium text-ink-gray-8">{{ name }}</p>
					<p class="text-p-xs text-ink-gray-5">Now · Anyone</p>
				</div>
				<PlatformIcon provider="LinkedIn" class="ml-auto size-4 text-ink-gray-5" />
			</div>

			<p class="mt-3 whitespace-pre-wrap break-words text-p-base text-ink-gray-8">
				<template v-if="body(0).kept || body(0).over">
					{{ body(0).kept
					}}<span v-if="body(0).over" class="bg-surface-red-2 text-ink-red-4">{{
						body(0).over
					}}</span>
				</template>
				<span v-else class="text-ink-gray-4">Your post shows up here.</span>
			</p>
		</div>

		<!-- Parts after the first become comments under the post, so they stack and indent. -->
		<div
			v-for="(text, index) in comments"
			:key="index"
			class="ml-6 rounded-6 border border-outline-gray-2 bg-surface-gray-1 p-3"
		>
			<div class="flex items-center gap-2">
				<Avatar :image="channel?.avatar_url ?? undefined" :label="name" size="sm" />
				<p class="truncate text-p-xs font-medium text-ink-gray-7">{{ name }}</p>
			</div>
			<p class="mt-2 whitespace-pre-wrap break-words text-p-sm text-ink-gray-8">
				{{ body(index + 1).kept
				}}<span v-if="body(index + 1).over" class="bg-surface-red-2 text-ink-red-4">{{
					body(index + 1).over
				}}</span>
			</p>
		</div>

		<p v-for="error in errors" :key="error" class="text-p-sm text-ink-red-3">{{ error }}</p>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Avatar } from 'frappe-ui'
import PlatformIcon from '@/components/social/PlatformIcon.vue'
import type { SocialChannel } from '@/types'

/** The post as LinkedIn shows it: the feed card, then each comment under it. */
const props = withDefaults(
	defineProps<{
		channel?: SocialChannel
		/** Part 1 first */
		texts: string[]
		limit: number
		errors?: string[]
	}>(),
	{ errors: () => [] },
)

const name = computed(() => props.channel?.display_name ?? 'LinkedIn')

const comments = computed(() => props.texts.slice(1))

/** What LinkedIn would keep, and what falls past the limit. */
function body(index: number): { kept: string; over: string } {
	const text = props.texts[index] ?? ''
	if (!props.limit || text.length <= props.limit) return { kept: text, over: '' }
	return { kept: text.slice(0, props.limit), over: text.slice(props.limit) }
}
</script>
