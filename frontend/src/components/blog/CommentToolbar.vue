<template>
	<div class="flex min-h-8 flex-wrap items-center gap-2">
		<template v-if="selectedCount">
			<span class="text-sm text-ink-gray-8">{{ selectedCount }} selected</span>
			<Button
				label="Hide"
				icon-left="lucide-eye-off"
				:loading="busy"
				@click="emit('set-hidden', true)"
			/>
			<Button
				label="Unhide"
				icon-left="lucide-eye"
				:loading="busy"
				@click="emit('set-hidden', false)"
			/>
			<Button
				theme="red"
				label="Delete"
				icon-left="lucide-trash-2"
				:disabled="busy"
				@click="emit('delete')"
			/>
			<Button variant="ghost" label="Clear" icon-left="lucide-x" @click="emit('clear')" />
		</template>

		<template v-else>
			<TabButtons v-model="status" :options="STATUS_OPTIONS" />
			<TextInput
				v-model="search"
				class="w-full sm:w-64"
				placeholder="Search name, email, comment…"
				aria-label="Search comments"
			>
				<template #prefix>
					<span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" />
				</template>
			</TextInput>
			<span class="ml-auto text-sm text-ink-gray-5">{{ summary }}</span>
		</template>
	</div>
</template>

<script setup lang="ts">
import { Button, TabButtons, TextInput } from 'frappe-ui'
import type { CommentStatus } from '@/lib/blogComments'

/** Filters above the comment groups. With rows selected, it turns into the bulk actions. */
defineProps<{ selectedCount: number; summary: string; busy: boolean }>()

const status = defineModel<CommentStatus>('status', { required: true })
const search = defineModel<string>('search', { required: true })

const emit = defineEmits<{ 'set-hidden': [hidden: boolean]; delete: []; clear: [] }>()

const STATUS_OPTIONS = [
	{ label: 'All', value: '' },
	{ label: 'Visible', value: 'visible' },
	{ label: 'Hidden', value: 'hidden' },
]
</script>
