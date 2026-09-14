<template>
	<div class="divide-y divide-outline-gray-1" aria-busy="true" aria-label="Loading">
		<div class="flex h-8 items-center gap-4">
			<Skeleton class="h-3 w-24 rounded" />
			<Skeleton class="ml-auto h-3 w-16 rounded" />
		</div>
		<div v-for="row in rows" :key="row" class="flex h-11 items-center gap-4">
			<Skeleton class="h-4 rounded" :class="WIDTHS[row % WIDTHS.length]" />
			<Skeleton class="ml-auto h-4 w-20 rounded" />
		</div>
	</div>
</template>

<script setup lang="ts">
import { Skeleton } from 'frappe-ui'

withDefaults(defineProps<{ rows?: number }>(), { rows: 5 })

/** Varied widths, so the rows read as text and not as a grid */
const WIDTHS = ['w-2/5', 'w-1/3', 'w-1/2', 'w-1/4']
</script>
