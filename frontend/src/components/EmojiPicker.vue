<template>
	<Popover :side="side" :align="align">
		<template #trigger="triggerProps">
			<slot name="trigger" v-bind="triggerProps">
				<Button variant="subtle" :aria-label="`Emoji: ${model || 'none'}`">
					<span class="text-lg leading-none">{{ model || '🙂' }}</span>
				</Button>
			</slot>
		</template>

		<!-- Copied from Gameplan's EmojiPicker, without custom emojis. -->
		<template #default="{ close }">
			<ScrollArea class="h-96 w-[22rem]" viewport-class="pb-2.5">
				<div class="sticky top-0 z-20 flex gap-2 bg-surface-elevation-2 px-2.5 pt-2.5">
					<TextInput v-model="search" v-focus class="flex-1" placeholder="Search by keyword" />
					<Button label="Random" @click="select(randomEmoji(), close)" />
				</div>

				<div v-for="(emojis, category) in groups" :key="category">
					<p class="sticky top-10 z-10 bg-surface-elevation-2 px-2.5 pb-2 pt-3 text-sm text-ink-gray-6">
						{{ category }}
					</p>
					<div class="grid grid-cols-10 place-items-center px-2.5">
						<button
							v-for="emoji in emojis"
							:key="emoji.description"
							type="button"
							class="size-8 rounded-5 text-2xl leading-none hover:bg-surface-gray-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
							:title="emoji.description"
							@click="select(emoji.emoji, close)"
						>
							{{ emoji.emoji }}
						</button>
					</div>
				</div>

				<p v-if="!Object.keys(groups).length" class="px-2.5 py-8 text-center text-sm text-ink-gray-5">
					No emoji matches “{{ search }}”
				</p>
			</ScrollArea>
		</template>
	</Popover>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Button, Popover, ScrollArea, TextInput, vFocus } from 'frappe-ui'
import { gemoji, type Gemoji } from 'gemoji'

withDefaults(
	defineProps<{
		side?: 'top' | 'right' | 'bottom' | 'left'
		align?: 'start' | 'center' | 'end'
	}>(),
	{ side: 'bottom', align: 'start' },
)

const model = defineModel<string>({ default: '' })

const search = ref('')

const groups = computed(() => {
	const query = search.value.trim().toLowerCase()
	const byCategory: Record<string, Gemoji[]> = {}
	for (const emoji of gemoji) {
		if (query && !keywords(emoji).includes(query)) continue
		;(byCategory[emoji.category] ??= []).push(emoji)
	}
	return byCategory
})

function select(emoji: string, close: () => void) {
	model.value = emoji
	search.value = ''
	close()
}

function keywords(emoji: Gemoji) {
	return [emoji.description, ...emoji.names, ...emoji.tags].join(' ').toLowerCase()
}

function randomEmoji() {
	return gemoji[Math.floor(Math.random() * gemoji.length)].emoji
}
</script>
