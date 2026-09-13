<template>
	<MultiSelect v-model="model" label="Tags" placeholder="Pick or create tags" :options="options">
		<template #footer="{ query, setOpen }">
			<div class="border-t border-outline-gray-1 px-2 py-1.5">
				<Button
					v-if="canCreate(query)"
					variant="ghost"
					icon-left="lucide-plus"
					:label="`Create “${query.trim()}”`"
					class="w-full justify-start"
					@click="create(query, setOpen)"
				/>
				<p v-else class="px-1 text-sm text-ink-gray-5">Type to create a new tag.</p>
			</div>
		</template>
	</MultiSelect>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Button, MultiSelect, useList } from 'frappe-ui'
import type { SubscriberTag } from '@/types'

const model = defineModel<string[]>({ required: true })

const savedTags = useList<SubscriberTag>({
	doctype: 'Subscriber Tag',
	fields: ['name', 'tag_name'],
	orderBy: 'tag_name asc',
	limit: 1000,
})

// New tags exist only here until the subscriber is saved. The server creates them.
const draftTags = ref<string[]>([])

const options = computed(() => {
	const names = new Set([...(savedTags.data ?? []).map((tag) => tag.name), ...draftTags.value])
	return [...names].map((name) => ({ label: name, value: name }))
})

function canCreate(query: string) {
	const name = query.trim()
	return Boolean(name) && !options.value.some((option) => option.value === name)
}

function create(query: string, setOpen: (open: boolean) => void) {
	const name = query.trim()
	draftTags.value.push(name)
	model.value = [...model.value, name]
	setOpen(false)
}
</script>
