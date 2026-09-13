<template>
	<PageHeader>
		<div class="min-w-0 flex-1">
			<Breadcrumbs :items="breadcrumbs" />
		</div>
		<Button
			variant="solid"
			theme="gray"
			label="Save"
			:loading="leadMagnet.setValue.loading"
			:disabled="!dirty"
			@click="save"
		/>
	</PageHeader>

	<div class="mx-auto max-w-2xl space-y-8 px-3 py-6 pb-20 sm:px-5">
		<LoadingText v-if="!leadMagnet.doc && !leadMagnet.error" :lines="6" />
		<ErrorMessage v-else-if="leadMagnet.error" :message="errorMessage(leadMagnet.error)" />

		<template v-else>
			<section class="space-y-4">
				<TextInput v-model="draft.title" label="Title" required />
				<Textarea
					v-model="draft.description"
					label="Description"
					description="For you. Subscribers do not see it."
					:rows="2"
				/>
				<LeadMagnetFileInput v-model="draft.file" />
			</section>

			<section class="space-y-1">
				<h2 class="text-lg-semibold text-ink-gray-8">Downloads</h2>
				<p class="text-p-base text-ink-gray-6">
					<span class="tabular-nums">{{ downloadCount }}</span>
					{{ downloadCount === 1 ? 'download' : 'downloads' }} from welcome email links.
				</p>
			</section>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, reactive, watch } from 'vue'
import {
	Breadcrumbs,
	Button,
	ErrorMessage,
	LoadingText,
	PageHeader,
	TextInput,
	Textarea,
	toast,
	useCall,
	useDoc,
} from 'frappe-ui'
import LeadMagnetFileInput from '@/components/lead-magnets/LeadMagnetFileInput.vue'
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

const draft = reactive({ title: '', description: '', file: '' })

const breadcrumbs = computed(() => [
	{ label: 'Lead Magnets', route: '/lead-magnets' },
	{ label: leadMagnet.doc?.title ?? props.leadMagnetId },
])

const saved = computed(() => {
	const doc = leadMagnet.doc
	if (!doc) return null
	return { title: doc.title, description: doc.description ?? '', file: doc.file }
})

const dirty = computed(
	() => Boolean(saved.value) && JSON.stringify(saved.value) !== JSON.stringify(draft),
)

// Load the draft on first fetch and again after each save.
watch(saved, (value) => value && Object.assign(draft, value), { immediate: true })

async function save() {
	try {
		await leadMagnet.setValue.submit({ ...draft })
		toast.success('Lead magnet saved')
	} catch (error) {
		toast.error(errorMessage(error as Error))
	}
}
</script>
