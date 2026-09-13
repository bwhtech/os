<template>
	<div class="space-y-3">
		<div class="flex justify-center">
			<TabButtons v-model="width" :options="WIDTHS" />
		</div>
		<LoadingText v-if="html === null" :lines="6" />
		<div v-else class="flex justify-center rounded-6 bg-surface-gray-2 p-4">
			<!-- Email HTML is a full document, so an iframe shows it the way an email client does. -->
			<iframe
				:srcdoc="html"
				title="Email preview"
				sandbox="allow-popups allow-popups-to-escape-sandbox"
				class="h-[48rem] max-w-full rounded-4 bg-white shadow-sm transition-[width]"
				:style="{ width: `${width}px` }"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { LoadingText, TabButtons } from 'frappe-ui'

/** Null while the HTML is being made */
defineProps<{ html: string | null }>()

const WIDTHS = [
	{ label: 'Desktop', value: 680 },
	{ label: 'Mobile', value: 375 },
]

const width = ref(680)
</script>
