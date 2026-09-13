<template>
	<PageHeader>
		<div class="min-w-0 flex-1">
			<Breadcrumbs :items="breadcrumbs" />
		</div>
		<div class="flex shrink-0 gap-2">
			<Button
				label="Send Test"
				icon-left="lucide-send"
				:loading="sendTest.loading"
				:disabled="!issue.doc"
				@click="sendTestEmail"
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

	<div class="mx-auto max-w-3xl space-y-6 px-3 py-6 pb-20 sm:px-5">
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

			<TabButtons v-model="tab" :options="TABS" />

			<!-- v-show keeps the editor and its undo history while the preview is open. -->
			<EmailEditor v-show="tab === 'write'" ref="editor" v-model="draft.content" />
			<EmailPreview v-if="tab === 'preview'" :html="previewHtml" />
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, useTemplateRef, watch } from 'vue'
import {
	Breadcrumbs,
	Button,
	ErrorMessage,
	LoadingText,
	PageHeader,
	TabButtons,
	TextInput,
	toast,
	useCall,
	useDoc,
} from 'frappe-ui'
import EmailEditor from '@/components/newsletters/EmailEditor.vue'
import EmailPreview from '@/components/newsletters/EmailPreview.vue'
import { errorMessage } from '@/lib/errors'
import type { EmailDocument, NewsletterIssue } from '@/types'

const props = defineProps<{ issueId: string }>()

const TABS = [
	{ label: 'Write', value: 'write' },
	{ label: 'Preview', value: 'preview' },
]

const issue = useDoc<NewsletterIssue>({
	doctype: 'Newsletter Issue',
	name: computed(() => props.issueId),
})

const sendTest = useCall<string, { issue: string }>({
	url: '/api/v2/method/bwh_os.mailing.api.send_test_newsletter',
	method: 'POST',
	immediate: false,
})

const editor = useTemplateRef<InstanceType<typeof EmailEditor>>('editor')
const tab = ref<'write' | 'preview'>('write')
const previewHtml = ref<string | null>(null)
const saving = ref(false)
/** The editor reads its content once, so it mounts only after the first fetch. */
const loaded = ref(false)

const draft = reactive({
	subject: '',
	previewText: '',
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
async function sendTestEmail() {
	if (dirty.value) await save()
	if (dirty.value) return
	const recipient = await sendTest.submit({ issue: props.issueId })
	if (recipient) toast.success(`Test sent to ${recipient}`)
	else if (sendTest.error) toast.error(errorMessage(sendTest.error))
}

function parseContent(value: NewsletterIssue['content_json']): EmailDocument | null {
	if (!value) return null
	return typeof value === 'string' ? JSON.parse(value) : value
}
</script>
