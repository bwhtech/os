<template>
	<AppPageHeader :breadcrumbs="breadcrumbs">
		<template #actions>
			<Tooltip :text="sendTooltip" :disabled="!sendTooltip">
				<Button label="Send to…" :disabled="!canSendManually" @click="sendOpen = true" />
			</Tooltip>
			<Button
				variant="solid"
				theme="gray"
				label="Save"
				:loading="leadMagnet.setValue.loading"
				:disabled="!dirty"
				@click="save"
			/>
		</template>
	</AppPageHeader>

	<SendLeadMagnetDialog
		v-model:open="sendOpen"
		:lead-magnet-id="leadMagnetId"
		:lead-magnet-title="leadMagnet.doc?.title ?? ''"
	/>

	<!-- Wide enough for the email editor and its inspector. Plain fields keep a narrow column. -->
	<div class="mx-auto max-w-5xl space-y-8 px-3 py-6 pb-20 sm:px-5">
		<DetailSkeleton v-if="!leadMagnet.doc && !leadMagnet.error" />
		<ErrorMessage v-else-if="leadMagnet.error" :message="errorMessage(leadMagnet.error)" />

		<template v-else>
			<ActivityCards
				method="bwh_os.mailing.api.get_lead_magnet_activity"
				:params="{ lead_magnet: leadMagnetId }"
				label="Downloads"
			/>

			<section class="max-w-2xl space-y-4">
				<TextInput v-model="draft.title" label="Title" required />
				<div class="space-y-1.5">
					<div class="text-xs text-ink-gray-5">Download page</div>
					<div class="flex items-center gap-2">
						<a
							:href="downloadUrl"
							target="_blank"
							class="truncate font-mono text-sm text-ink-gray-7 hover:text-ink-gray-9"
						>
							{{ downloadPath }}
						</a>
						<Button
							variant="ghost"
							icon="lucide-copy"
							aria-label="Copy download page URL"
							@click="copyUrl"
						/>
					</div>
					<p class="text-p-sm text-ink-gray-5">
						The link in an email adds the reader's token. Without one the page says the link
						is not valid.
					</p>
				</div>
				<Textarea
					v-model="draft.blurb"
					label="Blurb"
					description="One line on the download page. Subscribers see this."
					:rows="2"
				/>
				<Textarea
					v-model="draft.description"
					label="Description"
					description="For you. Subscribers do not see it."
					:rows="2"
				/>
				<LeadMagnetFileInput v-model="draft.file" />
				<TagPicker
					v-model="draft.tags"
					description="Everyone who downloads the file gets these tags. A new tag also goes to past downloads."
				/>
			</section>

			<!-- The editor reads its content once, so it mounts only after the first fetch. -->
			<LeadMagnetEmailSection
				v-if="loaded"
				ref="emailSection"
				v-model:subject="draft.subject"
				v-model:reply-to="draft.replyTo"
				v-model:content="draft.content"
				v-model:theme="draft.theme"
			/>

			<LeadMagnetDownloads :lead-magnet-id="leadMagnetId" :count="downloadCount" />
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, useTemplateRef, watch } from 'vue'
import {
	Button,
	ErrorMessage,
	TextInput,
	Textarea,
	Tooltip,
	toast,
	useCall,
	useDoc,
} from 'frappe-ui'
import AppPageHeader from '@/components/shell/AppPageHeader.vue'
import DetailSkeleton from '@/components/stats/DetailSkeleton.vue'
import LeadMagnetDownloads from '@/components/lead-magnets/LeadMagnetDownloads.vue'
import LeadMagnetEmailSection from '@/components/lead-magnets/LeadMagnetEmailSection.vue'
import LeadMagnetFileInput from '@/components/lead-magnets/LeadMagnetFileInput.vue'
import SendLeadMagnetDialog from '@/components/lead-magnets/SendLeadMagnetDialog.vue'
import TagPicker from '@/components/tags/TagPicker.vue'
import ActivityCards from '@/components/stats/ActivityCards.vue'
import { useSaveShortcut } from '@/composables/useSaveShortcut'
import { useUnsavedChanges } from '@/composables/useUnsavedChanges'
import { errorMessage } from '@/lib/errors'
import { leadMagnetStarter, parseEmailDocument } from '@/lib/emailStarters'
import type { EmailDocument, LeadMagnet, NewsletterTheme } from '@/types'

const props = defineProps<{ leadMagnetId: string }>()

const leadMagnet = useDoc<LeadMagnet>({
	doctype: 'Lead Magnet',
	name: computed(() => props.leadMagnetId),
})

const counts = useCall<Record<string, number>>({
	url: '/api/v2/method/bwh_os.mailing.api.get_download_counts',
})

const downloadCount = computed(() => counts.data?.[props.leadMagnetId] ?? 0)

const emailSection = useTemplateRef<InstanceType<typeof LeadMagnetEmailSection>>('emailSection')
const loaded = ref(false)
const sendOpen = ref(false)

const draft = reactive({
	title: '',
	blurb: '',
	description: '',
	file: '',
	tags: [] as string[],
	subject: '',
	replyTo: '',
	content: null as EmailDocument | null,
	theme: 'Frappe UI' as NewsletterTheme,
})

const breadcrumbs = computed(() => [
	{ label: 'Lead Magnets', route: '/lead-magnets' },
	{ label: leadMagnet.doc?.title ?? props.leadMagnetId },
])

// The route is set by the server from the title, so it lags a rename until the save lands.
const downloadPath = computed(() => `/download/${leadMagnet.doc?.route ?? ''}`)
const downloadUrl = computed(() => new URL(downloadPath.value, window.location.origin).href)

const saved = computed(() => {
	const doc = leadMagnet.doc
	if (!doc) return null
	return {
		title: doc.title,
		blurb: doc.blurb ?? '',
		description: doc.description ?? '',
		file: doc.file,
		tags: doc.tags.map((row) => row.tag),
		subject: doc.subject ?? '',
		replyTo: doc.reply_to ?? '',
		// A magnet with no email yet starts from a first draft.
		content: parseEmailDocument(doc.content_json) ?? leadMagnetStarter(),
		theme: doc.theme,
	}
})

const dirty = computed(
	() => Boolean(saved.value) && JSON.stringify(saved.value) !== JSON.stringify(draft),
)

// A manual send reads the saved document, not the draft, so it must not run ahead of a save.
const sendTooltip = computed(() => {
	if (!leadMagnet.doc?.subject || !leadMagnet.doc?.content_html) {
		return 'Write and save the delivery email first.'
	}
	if (dirty.value) return 'Save your changes first.'
	return ''
})
const canSendManually = computed(() => !sendTooltip.value)

useUnsavedChanges(dirty, 'This lead magnet has changes that are not saved. Leave anyway?')

/**
 * Load the draft once per lead magnet. A document that comes back from the server, after a
 * save or on its own, must not overwrite what is being typed.
 */
const loadedName = ref('')

watch(
	saved,
	(value) => {
		const name = leadMagnet.doc?.name
		if (!value || !name || name === loadedName.value) return
		loadedName.value = name
		Object.assign(draft, structuredClone(value))
		loaded.value = true
	},
	{ immediate: true },
)

async function copyUrl() {
	await navigator.clipboard.writeText(downloadUrl.value)
	toast.success('Link copied')
}

async function save() {
	try {
		await leadMagnet.setValue.submit({
			title: draft.title,
			blurb: draft.blurb,
			description: draft.description,
			file: draft.file,
			tags: draft.tags.map((tag) => ({ tag })),
			subject: draft.subject,
			reply_to: draft.replyTo || null,
			theme: draft.theme,
			content_json: JSON.stringify(draft.content),
			// A hidden editor keeps the saved email.
			content_html: (await emailSection.value?.getHtml()) ?? leadMagnet.doc?.content_html,
		})
		toast.success('Lead magnet saved')
	} catch (error) {
		toast.error(errorMessage(error as Error))
	}
}

useSaveShortcut(() => {
	if (dirty.value && !leadMagnet.setValue.loading) save()
})
</script>
