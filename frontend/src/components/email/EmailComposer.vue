<template>
	<div class="space-y-3">
		<div class="flex flex-wrap items-center justify-between gap-2">
			<TabButtons v-model="tab" :options="TABS" />
			<Select v-model="theme" :options="THEMES" class="w-36" aria-label="Theme" />
		</div>

		<div v-if="variables.length" class="flex flex-wrap items-center gap-1.5 text-p-sm text-ink-gray-5">
			<span>Type <code v-pre class="font-mono text-ink-gray-7">{{</code> to add</span>
			<Tooltip v-for="variable in variables" :key="variable.key" :text="describe(variable)">
				<Badge :label="variable.label" theme="blue" variant="subtle" />
			</Tooltip>
			<span v-if="tab === 'preview'">The preview shows sample values.</span>
		</div>

		<!-- v-show keeps the editor and its undo history while the preview is open. -->
		<EmailEditor
			v-show="tab === 'write'"
			ref="editor"
			v-model="content"
			:theme="theme"
			:variables="variables"
		/>
		<EmailPreview v-if="tab === 'preview'" :html="previewHtml" />
	</div>
</template>

<script setup lang="ts">
import { ref, useTemplateRef, watch } from 'vue'
import { Badge, Select, TabButtons, Tooltip } from 'frappe-ui'
import EmailEditor from '@/components/email/EmailEditor.vue'
import EmailPreview from '@/components/email/EmailPreview.vue'
import { describe } from '@/components/email/email-editor/variables'
import { fillFooter } from '@/lib/emailFooter'
import { fillSamples, type EmailVariable } from '@/lib/emailVariables'
import type { EmailDocument, NewsletterTheme } from '@/types'

/** The editor, a preview with sample values, and the theme picker. Used for every email in OS. */
const props = withDefaults(
	defineProps<{
		variables?: EmailVariable[]
		/** Inbox apps show it after the subject */
		previewText?: string
	}>(),
	{ variables: () => [], previewText: '' },
)

const content = defineModel<EmailDocument | null>('content', { required: true })
const theme = defineModel<NewsletterTheme>('theme', { required: true })

const TABS = [
	{ label: 'Write', value: 'write' },
	{ label: 'Preview', value: 'preview' },
]

const THEMES: NewsletterTheme[] = ['Frappe UI', 'Basic', 'Minimal']

const editor = useTemplateRef<InstanceType<typeof EmailEditor>>('editor')
const tab = ref<'write' | 'preview'>('write')
const previewHtml = ref<string | null>(null)

watch(tab, async (value) => {
	if (value !== 'preview') return
	previewHtml.value = null
	previewHtml.value = fillSamples(await fillFooter(await getHtml()), props.variables)
})

function getHtml() {
	return editor.value?.getHtml(props.previewText) ?? Promise.resolve('')
}

defineExpose({
	/** Email HTML for the current content, with the variables left in. Empty until the editor is ready. */
	getHtml,
})
</script>
