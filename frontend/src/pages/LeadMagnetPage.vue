<template>
	<AppPageHeader :breadcrumbs="breadcrumbs">
		<template #actions>
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

	<div class="mx-auto max-w-2xl space-y-8 px-3 py-6 pb-20 sm:px-5">
		<DetailSkeleton v-if="!leadMagnet.doc && !leadMagnet.error" />
		<ErrorMessage v-else-if="leadMagnet.error" :message="errorMessage(leadMagnet.error)" />

		<template v-else>
			<ActivityCards
				method="bwh_os.mailing.api.get_lead_magnet_activity"
				:params="{ lead_magnet: leadMagnetId }"
				label="Downloads"
			/>

			<section class="space-y-4">
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
			</section>

			<LeadMagnetDownloads :lead-magnet-id="leadMagnetId" :count="downloadCount" />
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import {
	Button,
	ErrorMessage,
	TextInput,
	Textarea,
	toast,
	useCall,
	useDoc,
} from 'frappe-ui'
import AppPageHeader from '@/components/shell/AppPageHeader.vue'
import DetailSkeleton from '@/components/stats/DetailSkeleton.vue'
import LeadMagnetDownloads from '@/components/lead-magnets/LeadMagnetDownloads.vue'
import LeadMagnetFileInput from '@/components/lead-magnets/LeadMagnetFileInput.vue'
import ActivityCards from '@/components/stats/ActivityCards.vue'
import { useSaveShortcut } from '@/composables/useSaveShortcut'
import { useUnsavedChanges } from '@/composables/useUnsavedChanges'
import { errorMessage } from '@/lib/errors'
import type { LeadMagnet } from '@/types'

const props = defineProps<{ leadMagnetId: string }>()

const leadMagnet = useDoc<LeadMagnet>({
	doctype: 'Lead Magnet',
	name: computed(() => props.leadMagnetId),
})

const counts = useCall<Record<string, number>>({
	url: '/api/v2/method/bwh_os.mailing.api.get_download_counts',
})

const downloadCount = computed(() => counts.data?.[props.leadMagnetId] ?? 0)

const draft = reactive({ title: '', blurb: '', description: '', file: '' })

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
	}
})

const dirty = computed(
	() => Boolean(saved.value) && JSON.stringify(saved.value) !== JSON.stringify(draft),
)

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
		Object.assign(draft, value)
	},
	{ immediate: true },
)

async function copyUrl() {
	await navigator.clipboard.writeText(downloadUrl.value)
	toast.success('Link copied')
}

async function save() {
	try {
		await leadMagnet.setValue.submit({ ...draft })
		toast.success('Lead magnet saved')
	} catch (error) {
		toast.error(errorMessage(error as Error))
	}
}

useSaveShortcut(() => {
	if (dirty.value && !leadMagnet.setValue.loading) save()
})
</script>
