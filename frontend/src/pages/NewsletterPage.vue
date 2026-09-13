<template>
	<PageHeader>
		<div class="min-w-0 flex-1">
			<Breadcrumbs :items="breadcrumbs" />
		</div>
		<div class="flex shrink-0 gap-2">
			<Button
				label="Send Test"
				icon-left="lucide-send"
				:disabled="!issue.doc"
				@click="sendTestOpen = true"
			/>
			<Button
				variant="solid"
				theme="gray"
				label="Save"
				:loading="saving"
				:disabled="!dirty"
				@click="save"
			/>
		</div>
	</PageHeader>

	<!-- Wide enough for the 600px email and the inspector side by side. -->
	<div class="mx-auto max-w-5xl space-y-6 px-3 py-6 pb-20 sm:px-5">
		<LoadingText v-if="!issue.doc && !issue.error" :lines="6" />
		<ErrorMessage v-else-if="issue.error" :message="errorMessage(issue.error)" />

		<template v-else-if="loaded">
			<section class="space-y-4">
				<TextInput v-model="draft.subject" label="Subject" required />
				<TextInput
					v-model="draft.previewText"
					label="Preview text"
					description="Inbox apps show it after the subject."
				/>
			</section>

			<div class="flex flex-wrap items-center justify-between gap-2">
				<TabButtons v-model="tab" :options="TABS" />
				<Select v-model="draft.theme" :options="THEMES" class="w-36" aria-label="Theme" />
			</div>

			<!-- v-show keeps the editor and its undo history while the preview is open. -->
			<EmailEditor
				v-show="tab === 'write'"
				ref="editor"
				v-model="draft.content"
				:theme="draft.theme"
			/>
			<EmailPreview v-if="tab === 'preview'" :html="previewHtml" />
		</template>
	</div>

	<SendTestDialog v-model:open="sendTestOpen" :issue-id="issueId" :save="saveIfDirty" />
</template>

<script setup lang="ts">
import { computed, reactive, ref, useTemplateRef, watch } from 'vue'
import {
	Breadcrumbs,
	Button,
	ErrorMessage,
	LoadingText,
	PageHeader,
	Select,
	TabButtons,
	TextInput,
	toast,
	useDoc,
} from 'frappe-ui'
import EmailEditor from '@/components/newsletters/EmailEditor.vue'
import EmailPreview from '@/components/newsletters/EmailPreview.vue'
import SendTestDialog from '@/components/newsletters/SendTestDialog.vue'
import { errorMessage } from '@/lib/errors'
import type { EmailDocument, NewsletterIssue, NewsletterTheme } from '@/types'

const props = defineProps<{ issueId: string }>()

const TABS = [
	{ label: 'Write', value: 'write' },
	{ label: 'Preview', value: 'preview' },
]

const THEMES: NewsletterTheme[] = ['Frappe UI', 'Basic', 'Minimal']

const issue = useDoc<NewsletterIssue>({
	doctype: 'Newsletter Issue',
	name: computed(() => props.issueId),
})

const editor = useTemplateRef<InstanceType<typeof EmailEditor>>('editor')
const tab = ref<'write' | 'preview'>('write')
const previewHtml = ref<string | null>(null)
const saving = ref(false)
const sendTestOpen = ref(false)
/** The editor reads its content once, so it mounts only after the first fetch. */
const loaded = ref(false)

const draft = reactive({
	subject: '',
	previewText: '',
	theme: 'Frappe UI' as NewsletterTheme,
	content: null as EmailDocument | null,
})

const breadcrumbs = computed(() => [
	{ label: 'Newsletters', route: '/newsletters' },
	{ label: issue.doc?.subject ?? props.issueId },
])

const saved = computed(() => {
	const doc = issue.doc
	if (!doc) return null
	return {
		subject: doc.subject,
		previewText: doc.preview_text ?? '',
		theme: doc.theme,
		content: parseContent(doc.content_json),
	}
})

const dirty = computed(
	() => Boolean(saved.value) && JSON.stringify(saved.value) !== JSON.stringify(draft),
)

watch(
	saved,
	(value) => {
		if (!value || loaded.value) return
		Object.assign(draft, structuredClone(value))
		loaded.value = true
	},
	{ immediate: true },
)

watch(tab, async (value) => {
	if (value !== 'preview') return
	previewHtml.value = null
	previewHtml.value = (await editor.value?.getHtml(draft.previewText)) ?? ''
})

async function save() {
	saving.value = true
	try {
		await issue.setValue.submit({
			subject: draft.subject,
			preview_text: draft.previewText,
			theme: draft.theme,
			content_json: JSON.stringify(draft.content),
			content_html: (await editor.value?.getHtml(draft.previewText)) ?? '',
		})
		toast.success('Newsletter saved')
	} catch (error) {
		toast.error(errorMessage(error as Error))
	} finally {
		saving.value = false
	}
}

/** The test uses the saved HTML, so unsaved changes are saved first. */
async function saveIfDirty() {
	if (dirty.value) await save()
	return !dirty.value
}

function parseContent(value: NewsletterIssue['content_json']): EmailDocument | null {
	if (!value) return null
	return typeof value === 'string' ? JSON.parse(value) : value
}
</script>
