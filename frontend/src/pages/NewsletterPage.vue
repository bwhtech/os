<template>
	<PageHeader>
		<div class="flex min-w-0 flex-1 items-center gap-2">
			<Breadcrumbs :items="breadcrumbs" />
			<Badge
				v-if="issue.doc && !isDraft"
				:label="issue.doc.status"
				:theme="STATUS_THEMES[issue.doc.status]"
				variant="subtle"
			/>
		</div>
		<div class="flex shrink-0 gap-2">
			<Button
				v-if="issue.doc?.status === 'Sent'"
				:label="issue.doc.is_public ? 'Public' : 'Publish'"
				icon-left="lucide-globe"
				@click="publishOpen = true"
			/>
			<Button
				label="Send Test"
				icon-left="lucide-flask-conical"
				:disabled="!issue.doc"
				@click="sendTestOpen = true"
			/>
			<template v-if="isDraft">
				<Button label="Save" :loading="saving" :disabled="!dirty" @click="save" />
				<Button
					variant="solid"
					theme="gray"
					icon-left="lucide-send"
					label="Send"
					@click="sendOpen = true"
				/>
			</template>
		</div>
	</PageHeader>

	<!-- Wide enough for the 600px email and the inspector side by side. -->
	<div class="mx-auto max-w-5xl space-y-6 px-3 py-6 pb-20 sm:px-5">
		<LoadingText v-if="!issue.doc && !issue.error" :lines="6" />
		<ErrorMessage v-else-if="issue.error" :message="errorMessage(issue.error)" />

		<template v-else-if="issue.doc?.status === 'Scheduled'">
			<Alert
				theme="blue"
				icon="lucide-calendar-clock"
				:title="`Sends on ${dayjs(issue.doc.scheduled_at).format('D MMM YYYY, h:mm A')}`"
				description="A scheduled newsletter cannot change. Unschedule it to edit."
				:primary-action="{
					label: 'Unschedule',
					loading: unscheduleCall.loading,
					onClick: unschedule,
				}"
			/>
			<h1 class="text-xl-semibold text-ink-gray-9">{{ issue.doc.subject }}</h1>
			<EmailPreview :html="issue.doc.content_html" />
		</template>

		<template v-else-if="issue.doc && !isDraft">
			<div class="space-y-1">
				<h1 class="text-xl-semibold text-ink-gray-9">{{ issue.doc.subject }}</h1>
				<p v-if="issue.doc.preview_text" class="text-p-base text-ink-gray-6">
					{{ issue.doc.preview_text }}
				</p>
			</div>

			<TabButtons v-model="sentTab" :options="SENT_TABS" />
			<NewsletterReport v-if="sentTab === 'report'" :issue="issue.doc" @refresh="issue.reload()" />
			<EmailPreview v-else :html="issue.doc.content_html" />
		</template>

		<template v-else-if="loaded">
			<section class="space-y-4">
				<TextInput v-model="draft.subject" label="Subject" required />
				<TextInput
					v-model="draft.previewText"
					label="Preview text"
					description="Inbox apps show it after the subject."
				/>
			</section>

			<NewsletterAudience
				v-model:audience="draft.audience"
				v-model:tags="draft.tags"
				v-model:hourly-limit="draft.hourlyLimit"
				:preview="audience"
			/>

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
	<PublishDialog
		v-if="issue.doc?.status === 'Sent'"
		v-model:open="publishOpen"
		:issue="issue.doc"
		:save="(values) => issue.setValue.submit(values)"
	/>
	<SendNewsletterDialog
		v-if="isDraft"
		v-model:open="sendOpen"
		:issue-id="issueId"
		:preview="audience"
		:save="saveIfDirty"
		@sent="issue.reload()"
	/>
</template>

<script setup lang="ts">
import { computed, reactive, ref, useTemplateRef, watch } from 'vue'
import {
	Alert,
	Badge,
	Breadcrumbs,
	Button,
	ErrorMessage,
	LoadingText,
	PageHeader,
	Select,
	TabButtons,
	TextInput,
	dayjs,
	toast,
	useCall,
	useDoc,
} from 'frappe-ui'
import EmailEditor from '@/components/newsletters/EmailEditor.vue'
import EmailPreview from '@/components/newsletters/EmailPreview.vue'
import NewsletterAudience from '@/components/newsletters/NewsletterAudience.vue'
import NewsletterReport from '@/components/newsletters/NewsletterReport.vue'
import PublishDialog from '@/components/newsletters/PublishDialog.vue'
import SendNewsletterDialog from '@/components/newsletters/SendNewsletterDialog.vue'
import SendTestDialog from '@/components/newsletters/SendTestDialog.vue'
import { useAudiencePreview } from '@/composables/useAudiencePreview'
import { errorMessage } from '@/lib/errors'
import { STATUS_THEMES } from '@/lib/newsletters'
import type {
	EmailDocument,
	NewsletterAudience as Audience,
	NewsletterIssue,
	NewsletterStatus,
	NewsletterTheme,
} from '@/types'

const props = defineProps<{ issueId: string }>()

const TABS = [
	{ label: 'Write', value: 'write' },
	{ label: 'Preview', value: 'preview' },
]

const SENT_TABS = [
	{ label: 'Report', value: 'report' },
	{ label: 'Email', value: 'email' },
]

const THEMES: NewsletterTheme[] = ['Frappe UI', 'Basic', 'Minimal']

const issue = useDoc<NewsletterIssue>({
	doctype: 'Newsletter Issue',
	name: computed(() => props.issueId),
})

const unscheduleCall = useCall<NewsletterStatus, { issue: string }>({
	url: '/api/v2/method/bwh_os.mailing.api.unschedule_newsletter',
	method: 'POST',
	immediate: false,
})

const editor = useTemplateRef<InstanceType<typeof EmailEditor>>('editor')
const tab = ref<'write' | 'preview'>('write')
const sentTab = ref<'report' | 'email'>('report')
const previewHtml = ref<string | null>(null)
const saving = ref(false)
const sendTestOpen = ref(false)
const sendOpen = ref(false)
const publishOpen = ref(false)
/** The editor reads its content once, so it mounts only after the first fetch. */
const loaded = ref(false)

const isDraft = computed(() => issue.doc?.status === 'Draft')

const draft = reactive({
	subject: '',
	previewText: '',
	theme: 'Frappe UI' as NewsletterTheme,
	audience: 'All Active' as Audience,
	tags: [] as string[],
	hourlyLimit: 0,
	content: null as EmailDocument | null,
})

const audience = useAudiencePreview(() => ({
	audience: draft.audience,
	tags: draft.tags,
	hourlyLimit: draft.hourlyLimit,
}))

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
		audience: doc.audience,
		tags: doc.tags.map((row) => row.tag),
		hourlyLimit: doc.hourly_limit,
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
			audience: draft.audience,
			tags: draft.tags.map((tag) => ({ tag })),
			hourly_limit: draft.hourlyLimit,
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

async function unschedule() {
	const status = await unscheduleCall.submit({ issue: props.issueId })
	if (!status) {
		toast.error(errorMessage(unscheduleCall.error))
		return
	}
	await issue.reload()
	toast.success('Newsletter is a draft again')
}

/** A test and a send use the saved HTML, so unsaved changes are saved first. */
async function saveIfDirty() {
	if (dirty.value) await save()
	return !dirty.value
}

function parseContent(value: NewsletterIssue['content_json']): EmailDocument | null {
	if (!value) return null
	return typeof value === 'string' ? JSON.parse(value) : value
}
</script>
