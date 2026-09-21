<template>
	<section class="space-y-4">
		<div class="space-y-1">
			<h2 class="text-lg-semibold text-ink-gray-8">Lead Magnet</h2>
			<p class="text-p-sm text-ink-gray-5">
				Optional. Every reader gets their own download link, so a newsletter that gives away a
				file cannot go in the web archive.
			</p>
		</div>

		<div class="flex flex-wrap items-end gap-3">
			<LeadMagnetPicker v-model="pickedMagnet" class="max-w-sm flex-1" />
			<Button
				v-if="leadMagnet"
				label="Use its email"
				:disabled="!magnet.doc?.content_json"
				@click="useItsEmail"
			/>
		</div>

		<!-- The save is refused without this link, and it is the one thing nobody can guess.
		     Better to say so while the newsletter is being written, with the fix one click away. -->
		<div
			v-if="needsDownloadLink"
			class="flex flex-wrap items-center gap-3 rounded-6 bg-surface-amber-1 px-3 py-2.5"
		>
			<p class="text-p-sm text-ink-gray-7">
				This newsletter names a lead magnet but has no download link, so it cannot be saved yet.
			</p>
			<Button class="ml-auto" label="Add download button" @click="emit('add-download-button')" />
		</div>
	</section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button, dialog, useDoc } from 'frappe-ui'
import LeadMagnetPicker from '@/components/lead-magnets/LeadMagnetPicker.vue'
import { parseEmailDocument } from '@/lib/emailStarters'
import type { EmailDocument, LeadMagnet } from '@/types'

const props = defineProps<{ content: EmailDocument | null }>()
const emit = defineEmits<{
	'use-email': [content: EmailDocument, subject: string]
	'add-download-button': []
}>()

const leadMagnet = defineModel<string>('leadMagnet', { required: true })

const magnet = useDoc<LeadMagnet>({
	doctype: 'Lead Magnet',
	name: computed(() => leadMagnet.value),
})

/**
 * `{{ download_url }}` cannot appear anywhere else in the document, so looking for the text
 * is enough. See the same check on the lead magnet's own delivery email.
 */
const linksDownloadUrl = computed(() => JSON.stringify(props.content ?? {}).includes('download_url'))
const needsDownloadLink = computed(() => Boolean(leadMagnet.value) && !linksDownloadUrl.value)

/**
 * Un-picking the magnet while the download button is still in the email would fail the save
 * with a message about an unfillable variable — a fix that reads like a bug. Ask first, so
 * clearing the picker is a choice rather than a surprise later.
 */
const pickedMagnet = computed({
	get: () => leadMagnet.value,
	set: (value: string) => {
		if (value || !leadMagnet.value || !linksDownloadUrl.value) {
			leadMagnet.value = value
			return
		}
		dialog.confirm({
			title: 'Remove the lead magnet?',
			message: 'The download button in the email still points at it. Remove the button first, or this cannot be saved.',
			confirmLabel: 'Remove anyway',
			theme: 'red',
			onConfirm: () => {
				leadMagnet.value = value
			},
		})
	},
})

function useItsEmail() {
	const content = parseEmailDocument(magnet.doc?.content_json ?? null)
	if (!content) return
	const apply = () => emit('use-email', content, magnet.doc?.subject ?? '')
	if (!props.content) {
		apply()
		return
	}
	dialog.confirm({
		title: 'Replace the email?',
		message: `This throws away what you have written and uses ${magnet.doc?.title ?? 'the lead magnet'}'s delivery email instead.`,
		confirmLabel: 'Replace',
		theme: 'red',
		onConfirm: apply,
	})
}
</script>
