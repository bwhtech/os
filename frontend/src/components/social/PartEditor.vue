<template>
	<div class="space-y-4">
		<div v-for="(part, index) in texts" :key="index" class="rounded-6 border border-outline-gray-2 p-3">
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
				:value="part"
				rows="4"
				:disabled="disabled"
				:placeholder="placeholder(index)"
				:aria-label="partLabel(index)"
				class="block w-full resize-y border-0 bg-transparent p-0 text-base text-ink-gray-8 placeholder:text-ink-gray-4 focus:ring-0 disabled:text-ink-gray-5"
				@input="write(index, $event)"
			/>
		</div>

		<Button
			v-if="!disabled"
			variant="ghost"
			icon-left="lucide-plus"
			:label="texts.length ? `Add a ${partName.toLowerCase()}` : 'Write the post'"
			@click="add"
		/>
	</div>
</template>

<script setup lang="ts">
import { Button } from 'frappe-ui'

/**
 * The text of each part of a post. Part 1 is the post itself; the parts after it are
 * the thread or the first comment, which is why they are named after the platform.
 */
const props = withDefaults(
	defineProps<{
		/** The length of each part as the platform counts it. Falls back to the text length. */
		counts?: number[]
		/** The character limit of the strictest platform picked, or 0 when nothing is picked. */
		limit?: number
		/** What part 2 and later are called on the platforms picked */
		partName?: string
		disabled?: boolean
	}>(),
	{ counts: () => [], limit: 0, partName: 'Comment' },
)

const texts = defineModel<string[]>({ required: true })

function write(index: number, event: Event) {
	const next = [...texts.value]
	next[index] = (event.target as HTMLTextAreaElement).value
	texts.value = next
}

function add() {
	texts.value = [...texts.value, '']
}

function remove(index: number) {
	texts.value = texts.value.filter((_, at) => at !== index)
}

function count(index: number): number {
	return props.counts[index] ?? texts.value[index]?.length ?? 0
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
