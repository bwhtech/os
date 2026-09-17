<template>
	<AppPageHeader :breadcrumbs="breadcrumbs">
		<template #title-suffix>
			<Badge
				v-if="issue.doc && !isDraft"
				:label="issue.doc.status"
				:theme="STATUS_THEMES[issue.doc.status]"
				variant="subtle"
			/>
		</template>
		<template #actions>
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
		</template>
		<!-- The narrow header keeps Save and folds the rest into a menu. -->
		<template #mobile-actions>
			<Button v-if="isDraft" label="Save" :loading="saving" :disabled="!dirty" @click="save" />
			<Dropdown :options="mobileMenu" align="end">
				<Button variant="ghost" size="md" icon="lucide-ellipsis" aria-label="More actions" />
			</Dropdown>
		</template>
	</AppPageHeader>

	<!-- Wide enough for the 600px email and the inspector side by side. -->
	<div class="mx-auto max-w-5xl space-y-6 px-3 py-6 pb-20 sm:px-5">
		<div v-if="!issue.doc && !issue.error" class="space-y-6" aria-busy="true" aria-label="Loading">
			<div v-for="field in 2" :key="field" class="space-y-1.5">
				<Skeleton class="h-3 w-24 rounded-4" />
				<Skeleton class="h-7 w-full rounded-4" />
			</div>
			<Skeleton class="h-[32rem] w-full rounded-6" />
		</div>
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
			<EmailPreview :html="sampleHtml" />
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
			<EmailPreview v-else :html="sampleHtml" />
		</template>

		<template v-else-if="loaded">
			<section class="space-y-4">
				<TextInput v-model="draft.subject" label="Subject" required />
				<TextInput
					v-model="draft.previewText"
					label="Preview text"
					description="Inbox apps show it after the subject."
				/>
				<TextInput
					v-model="draft.replyTo"
					type="email"
					label="Reply-to"
					placeholder="The address in Settings"
					description="Where a reply to this newsletter goes. Empty uses the address in Settings."
				/>
			</section>

			<NewsletterAudience
				v-model:audience="draft.audience"
				v-model:tags="draft.tags"
				v-model:hourly-limit="draft.hourlyLimit"
				:preview="audience"
			/>

			<EmailComposer
				ref="composer"
				v-model:content="draft.content"
				v-model:theme="draft.theme"
				:variables="NEWSLETTER_VARIABLES"
				:preview-text="draft.previewText"
			/>
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
	Button,
	Dropdown,
	ErrorMessage,
	Skeleton,
	TabButtons,
	TextInput,
	dayjs,
	toast,
	useCall,
	useDoc,
	type DropdownOptions,
} from 'frappe-ui'
import AppPageHeader from '@/components/shell/AppPageHeader.vue'
import EmailComposer from '@/components/email/EmailComposer.vue'
import EmailPreview from '@/components/email/EmailPreview.vue'
import NewsletterAudience from '@/components/newsletters/NewsletterAudience.vue'
import NewsletterReport from '@/components/newsletters/NewsletterReport.vue'
import PublishDialog from '@/components/newsletters/PublishDialog.vue'
import SendNewsletterDialog from '@/components/newsletters/SendNewsletterDialog.vue'
import SendTestDialog from '@/components/newsletters/SendTestDialog.vue'
import { useAudiencePreview } from '@/composables/useAudiencePreview'
import { parseEmailDocument } from '@/lib/emailStarters'
import { NEWSLETTER_VARIABLES, fillSamples } from '@/lib/emailVariables'
import { useSaveShortcut } from '@/composables/useSaveShortcut'
import { useUnsavedChanges } from '@/composables/useUnsavedChanges'
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

const SENT_TABS = [
	{ label: 'Report', value: 'report' },
	{ label: 'Email', value: 'email' },
]

const issue = useDoc<NewsletterIssue>({
	doctype: 'Newsletter Issue',
	name: computed(() => props.issueId),
})

const unscheduleCall = useCall<NewsletterStatus, { issue: string }>({
	url: '/api/v2/method/bwh_os.mailing.api.unschedule_newsletter',
	method: 'POST',
	immediate: false,
})

const composer = useTemplateRef<InstanceType<typeof EmailComposer>>('composer')
const sentTab = ref<'report' | 'email'>('report')
const saving = ref(false)
const sendTestOpen = ref(false)
const sendOpen = ref(false)
const publishOpen = ref(false)
/** The editor reads its content once, so it mounts only after the first fetch. */
const loaded = ref(false)

const isDraft = computed(() => issue.doc?.status === 'Draft')

/** A scheduled or sent issue shows the saved email with sample values. */
const sampleHtml = computed(() => fillSamples(issue.doc?.content_html ?? '', NEWSLETTER_VARIABLES))

const draft = reactive({
	subject: '',
	replyTo: '',
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

/** The header actions that do not fit the mobile header. */
const mobileMenu = computed<DropdownOptions>(() => {
	const doc = issue.doc
	if (!doc) return []
	return [
		...(isDraft.value
			? [{ label: 'Send', icon: 'lucide-send', onClick: () => (sendOpen.value = true) }]
			: []),
		{ label: 'Send Test', icon: 'lucide-flask-conical', onClick: () => (sendTestOpen.value = true) },
		...(doc.status === 'Sent'
			? [
					{
						label: doc.is_public ? 'Public' : 'Publish',
						icon: 'lucide-globe',
						onClick: () => (publishOpen.value = true),
					},
				]
			: []),
	]
})

const saved = computed(() => {
	const doc = issue.doc
	if (!doc) return null
	return {
		subject: doc.subject,
		replyTo: doc.reply_to ?? '',
		previewText: doc.preview_text ?? '',
		theme: doc.theme,
		audience: doc.audience,
		tags: doc.tags.map((row) => row.tag),
		hourlyLimit: doc.hourly_limit,
		content: parseEmailDocument(doc.content_json),
	}
})

const dirty = computed(
	() => Boolean(saved.value) && JSON.stringify(saved.value) !== JSON.stringify(draft),
)

useUnsavedChanges(dirty, 'This newsletter has changes that are not saved. Leave anyway?')

/** The newsletter the draft was read from. See the watcher below. */
const loadedName = ref('')

// Once per newsletter: a document that comes back from the server must not overwrite what
// is being written, and another newsletter must still load.
watch(
	saved,
	(value) => {
		const name = issue.doc?.name
		if (!value || !name || name === loadedName.value) return
		loadedName.value = name
		Object.assign(draft, structuredClone(value))
		loaded.value = true
	},
	{ immediate: true },
)

async function save() {
	saving.value = true
	try {
		await issue.setValue.submit({
			subject: draft.subject,
			reply_to: draft.replyTo || null,
			preview_text: draft.previewText,
			theme: draft.theme,
			audience: draft.audience,
			tags: draft.tags.map((tag) => ({ tag })),
			hourly_limit: draft.hourlyLimit,
			content_json: JSON.stringify(draft.content),
			content_html: (await composer.value?.getHtml()) ?? '',
		})
		toast.success('Newsletter saved')
	} catch (error) {
		toast.error(errorMessage(error as Error))
	} finally {
		saving.value = false
	}
}

// A sent newsletter has nothing left to save.
useSaveShortcut(() => {
	if (isDraft.value && dirty.value && !saving.value) save()
})

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
</script>
