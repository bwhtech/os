<template>
	<div class="space-y-5">
		<div class="space-y-2">
			<Progress :value="percent" size="md" />
			<p class="text-p-sm text-ink-gray-5">
				<template v-if="progress.status === 'Running'">
					{{ progress.done }} of {{ progress.total }} rows. You can close this dialog. The
					import keeps running.
				</template>
				<template v-else-if="progress.status === 'Done'">
					All {{ progress.total }} rows are done.
				</template>
				<template v-else>Stopped after {{ progress.done }} of {{ progress.total }} rows.</template>
			</p>
		</div>

		<div class="grid grid-cols-2 gap-2 sm:grid-cols-4">
			<div
				v-for="stat in stats"
				:key="stat.label"
				class="rounded-6 border border-outline-gray-1 px-3 py-2.5"
			>
				<p class="text-xl font-semibold text-ink-gray-9">{{ stat.value }}</p>
				<p class="text-p-sm text-ink-gray-5">{{ stat.label }}</p>
			</div>
		</div>

		<ErrorMessage v-if="progress.message" :message="progress.message" />

		<div v-if="progress.errors.length" class="space-y-2">
			<p class="text-sm text-ink-gray-5">Rows that failed</p>
			<ul class="divide-y divide-outline-gray-1 text-sm">
				<li
					v-for="error in progress.errors"
					:key="error.email"
					class="flex flex-wrap gap-x-3 py-2"
				>
					<span class="text-ink-gray-8">{{ error.email }}</span>
					<span class="text-ink-red-4">{{ error.error }}</span>
				</li>
			</ul>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ErrorMessage, Progress } from 'frappe-ui'
import type { ImportProgressEvent } from '@/types'

const props = defineProps<{ progress: ImportProgressEvent }>()

const percent = computed(() => {
	const { done, total } = props.progress
	return total ? Math.round((done / total) * 100) : 0
})

const stats = computed(() => {
	const { counts } = props.progress
	return [
		{ label: 'Added', value: counts.New },
		{ label: 'Tagged', value: counts.Existing },
		{ label: 'Skipped', value: counts.Invalid + counts.Duplicate },
		{ label: 'Failed', value: counts.Failed },
	]
})
</script>
