<template>
	<div class="space-y-4">
		<div v-for="(part, index) in parts" :key="index" class="rounded-6 border border-outline-gray-2 p-3">
			<div class="mb-2 flex items-center gap-2">
				<span class="text-p-sm font-medium text-ink-gray-7">{{ partLabel(index) }}</span>
				<span
					class="ml-auto text-p-sm tabular-nums"
					:class="over(index) ? 'text-ink-red-3' : 'text-ink-gray-5'"
				>
					{{ count(index) }}<span v-if="limit"> / {{ limit }}</span>
				</span>
				<Button
					v-if="index > 0 && !disabled"
					variant="ghost"
					size="sm"
					icon="lucide-trash-2"
					:aria-label="`Remove ${partLabel(index)}`"
					@click="remove(index)"
				/>
			</div>
			<textarea
				:value="part.text"
				rows="4"
				:disabled="disabled"
				:placeholder="placeholder(index)"
				:aria-label="partLabel(index)"
				class="block w-full resize-y border-0 bg-transparent p-0 text-base text-ink-gray-8 placeholder:text-ink-gray-4 focus:ring-0 disabled:text-ink-gray-5"
				@input="write(index, $event)"
			/>

			<!-- Only where the platforms take it: LinkedIn wants its comments in text alone. -->
			<MediaPicker
				v-if="postName && (index === 0 || mediaAfterPartOne)"
				:model-value="part.media"
				:post-name="postName"
				:max="maxImages"
				:max-image-bytes="maxImageBytes"
				:max-video-bytes="maxVideoBytes"
				:disabled="disabled"
				class="mt-3"
				@update:model-value="attach(index, $event)"
			/>
		</div>

		<Button
			v-if="!disabled"
			variant="ghost"
			icon-left="lucide-plus"
			:label="parts.length ? `Add a ${partName.toLowerCase()}` : 'Write the post'"
			@click="add"
		/>
	</div>
</template>

<script setup lang="ts">
import { Button } from 'frappe-ui'
import MediaPicker from '@/components/social/MediaPicker.vue'
import type { DraftPart } from '@/lib/social'
import type { SocialMedia } from '@/types'

/**
 * The parts of a post: the text and the images of each. Part 1 is the post itself; the
 * parts after it are the thread or the first comment, named after the platform.
 */
const props = withDefaults(
	defineProps<{
		/** The post the images attach to. Empty until the draft has been inserted. */
		postName?: string
		/** The length of each part as the platform counts it. Falls back to the text length. */
		counts?: number[]
		/** The character limit of the strictest platform picked, or 0 when nothing is picked. */
		limit?: number
		/** How many images the strictest platform picked takes in one part */
		maxImages?: number
		/** The biggest image and video the platforms picked take, in bytes */
		maxImageBytes?: number
		maxVideoBytes?: number
		/** Whether every platform picked takes media past part 1 */
		mediaAfterPartOne?: boolean
		/** What part 2 and later are called on the platforms picked */
		partName?: string
		disabled?: boolean
	}>(),
	{
		postName: '',
		counts: () => [],
		limit: 0,
		maxImages: 4,
		maxImageBytes: 0,
		maxVideoBytes: 0,
		partName: 'Comment',
	},
)

const parts = defineModel<DraftPart[]>({ required: true })

function replace(index: number, values: Partial<DraftPart>) {
	parts.value = parts.value.map((part, at) => (at === index ? { ...part, ...values } : part))
}

function write(index: number, event: Event) {
	replace(index, { text: (event.target as HTMLTextAreaElement).value })
}

function attach(index: number, media: SocialMedia[]) {
	replace(index, { media })
}

function add() {
	parts.value = [...parts.value, { text: '', media: [] }]
}

function remove(index: number) {
	parts.value = parts.value.filter((_, at) => at !== index)
}

function count(index: number): number {
	return props.counts[index] ?? parts.value[index]?.text.length ?? 0
}

function over(index: number): boolean {
	return Boolean(props.limit) && count(index) > props.limit
}

function partLabel(index: number): string {
	return index === 0 ? 'Post' : `${props.partName} ${index}`
}

function placeholder(index: number): string {
	return index === 0 ? 'What are you posting?' : 'Add to it'
}
</script>
