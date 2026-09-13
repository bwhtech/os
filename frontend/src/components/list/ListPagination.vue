<template>
	<nav
		class="flex flex-wrap items-center justify-between gap-3 text-sm text-ink-gray-6"
		aria-label="Pagination"
	>
		<div class="flex items-center gap-3">
			<span class="tabular-nums">
				<template v-if="total">
					<span class="text-ink-gray-8">{{ format(first) }}–{{ format(last) }}</span>
					of {{ format(total) }}
				</template>
				<template v-else>No rows</template>
			</span>
			<Select
				v-model="lengthValue"
				:options="lengthOptions"
				class="w-28"
				aria-label="Rows per page"
			/>
		</div>

		<div v-if="pageCount > 1" class="flex items-center gap-1">
			<Button
				variant="ghost"
				icon="lucide-chevron-left"
				aria-label="Previous page"
				:disabled="page === 1"
				@click="page = page - 1"
			/>
			<template v-for="(item, index) in pages" :key="index">
				<span v-if="item === GAP" class="w-7 text-center text-ink-gray-4" aria-hidden="true">…</span>
				<Button
					v-else
					:variant="item === page ? 'subtle' : 'ghost'"
					class="min-w-7 tabular-nums"
					:label="String(item)"
					:aria-current="item === page ? 'page' : undefined"
					@click="page = item"
				/>
			</template>
			<Button
				variant="ghost"
				icon="lucide-chevron-right"
				aria-label="Next page"
				:disabled="page === pageCount"
				@click="page = page + 1"
			/>
		</div>
	</nav>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { Button, Select } from 'frappe-ui'
import { PAGE_LENGTHS } from '@/composables/usePagedList'

const props = defineProps<{ total: number }>()

const page = defineModel<number>('page', { required: true })
const pageLength = defineModel<number>('pageLength', { required: true })

const GAP = 'gap' as const
/** Pages shown on each side of the current page */
const SIBLINGS = 1

const lengthOptions = PAGE_LENGTHS.map((length) => ({ label: `${length} / page`, value: String(length) }))

// Select works with strings.
const lengthValue = computed({
	get: () => String(pageLength.value),
	set: (value) => {
		pageLength.value = Number(value)
	},
})

const pageCount = computed(() => Math.max(1, Math.ceil(props.total / pageLength.value)))
const first = computed(() => (page.value - 1) * pageLength.value + 1)
const last = computed(() => Math.min(page.value * pageLength.value, props.total))

/** First, last, and the pages near the current one, with a gap where pages are left out. */
const pages = computed(() => {
	const count = pageCount.value
	const from = Math.max(2, page.value - SIBLINGS)
	const to = Math.min(count - 1, page.value + SIBLINGS)
	const items: Array<number | typeof GAP> = [1]
	if (from > 2) items.push(from === 3 ? 2 : GAP)
	for (let number = from; number <= to; number++) items.push(number)
	if (to < count - 1) items.push(to === count - 2 ? count - 1 : GAP)
	if (count > 1) items.push(count)
	return items
})

// A smaller total, after a filter or a delete, can leave the page past the end.
watch(pageCount, (count) => {
	if (page.value > count) page.value = count
})

function format(value: number) {
	return value.toLocaleString()
}
</script>
