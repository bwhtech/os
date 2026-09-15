<template>
	<!-- Matches a detail page: activity cards, then a column of fields -->
	<div class="space-y-8" aria-busy="true" aria-label="Loading">
		<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
			<Skeleton v-for="card in 2" :key="card" class="h-24 rounded-6" />
		</div>
		<div class="max-w-2xl space-y-5">
			<Skeleton class="h-5 w-32 rounded-4" />
			<div v-for="field in fields" :key="field" class="space-y-1.5">
				<Skeleton class="h-3 w-24 rounded-4" />
				<Skeleton class="h-7 w-full rounded-4" />
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Skeleton } from 'frappe-ui'

withDefaults(defineProps<{ fields?: number }>(), { fields: 3 })
</script>
