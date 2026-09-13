<template>
	<div class="flex flex-col items-center justify-center gap-3 py-16 text-center">
		<div class="rounded-full bg-surface-gray-2 p-3 text-ink-gray-5">
			<span class="lucide-mail size-6" aria-hidden="true" />
		</div>
		<template v-if="filtered">
			<p class="text-base text-ink-gray-7">No subscribers match these filters</p>
		</template>
		<template v-else>
			<p class="text-base text-ink-gray-7">No subscribers yet</p>
			<p class="text-sm text-ink-gray-5">Add the first one by hand or import a CSV file.</p>
			<div class="mt-2 flex gap-2">
				<Button icon-left="lucide-upload" label="Import" @click="emit('import')" />
				<Button
					variant="solid"
					theme="gray"
					icon-left="lucide-plus"
					label="Add Subscriber"
					@click="emit('add')"
				/>
			</div>
		</template>
	</div>
</template>

<script setup lang="ts">
import { Button } from 'frappe-ui'

defineProps<{ filtered: boolean }>()
const emit = defineEmits<{ add: []; import: [] }>()
</script>
