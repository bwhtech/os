<template>
	<MultiSelect
		v-model="model"
		:label="label"
		:description="description"
		placeholder="Pick or create tags"
		:options="options"
	>
		<template #footer="{ query, setOpen }">
			<div class="border-t border-outline-gray-1 px-2 py-1.5">
				<Button
					v-if="canCreate(query)"
					variant="ghost"
					icon-left="lucide-plus"
					:label="`Create “${query.trim()}”`"
					:loading="createTag.loading"
					class="w-full justify-start"
					@click="create(query, setOpen)"
				/>
				<p v-else class="px-1 text-sm text-ink-gray-5">Type to create a new tag.</p>
			</div>
		</template>
	</MultiSelect>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button, MultiSelect, toast, useCall, useList } from 'frappe-ui'
import type { SubscriberTag } from '@/types'

withDefaults(defineProps<{ label?: string; description?: string }>(), { label: 'Tags' })

const model = defineModel<string[]>({ required: true })

const savedTags = useList<SubscriberTag>({
	doctype: 'Subscriber Tag',
	fields: ['name'],
	orderBy: 'tag_name asc',
	limit: 1000,
})

// Create the tag right away: Frappe checks links before a parent document's save hooks run.
const createTag = useCall<SubscriberTag, { tag_name: string }>({
	url: '/api/v2/document/Subscriber Tag',
	method: 'POST',
	immediate: false,
	onError: (error) => toast.error(error.message),
})

const options = computed(() => {
	const names = new Set([...(savedTags.data ?? []).map((tag) => tag.name), ...model.value])
	return [...names].map((name) => ({ label: name, value: name }))
})

function canCreate(query: string) {
	const name = query.trim()
	return Boolean(name) && !options.value.some((option) => option.value === name)
}

async function create(query: string, setOpen: (open: boolean) => void) {
	const tag = await createTag.submit({ tag_name: query.trim() })
	if (!tag) return
	savedTags.reload()
	model.value = [...model.value, tag.name]
	setOpen(false)
}
</script>
