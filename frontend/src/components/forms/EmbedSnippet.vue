<template>
	<section class="space-y-3">
		<div class="flex items-center justify-between gap-2">
			<h2 class="text-lg-semibold text-ink-gray-8">Embed</h2>
			<Button icon-left="lucide-copy" label="Copy" @click="copy" />
		</div>
		<p class="text-p-sm text-ink-gray-5">
			Put this in an Astro page on bwh.tech. The form posts to the site's Netlify function, which
			sends the signup here.
		</p>
		<pre
			class="overflow-x-auto rounded-3 bg-surface-gray-2 p-3 font-mono text-sm text-ink-gray-8"
		><code>{{ snippet }}</code></pre>
	</section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button, toast } from 'frappe-ui'

const props = defineProps<{ formId: string; collectName: boolean }>()

const snippet = computed(() => {
	const attributes = ['client:visible', `formId="${props.formId}"`]
	if (props.collectName) attributes.push('collectName')
	return `<NewsletterForm ${attributes.join(' ')} />`
})

async function copy() {
	try {
		await navigator.clipboard.writeText(snippet.value)
		toast.success('Snippet copied')
	} catch {
		toast.error('Could not copy. Select the text and copy it by hand.')
	}
}
</script>
