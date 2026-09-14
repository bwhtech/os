<template>
	<Dialog v-model:open="open" :title="series ? 'Edit Series' : 'New Series'">
		<form class="space-y-4" @submit.prevent="submit">
			<div class="space-y-1.5">
				<FormLabel label="Title" size="md" required />
				<div class="flex gap-2">
					<EmojiPicker v-model="form.emoji" />
					<TextInput v-model="form.title" v-focus class="flex-1" placeholder="Frappe Framework Monthly" />
				</div>
			</div>
			<FormControl v-model="form.summary" type="textarea" label="Summary" :rows="3" />
			<ErrorMessage :message="error" />
			<div class="flex justify-end gap-2 pt-2">
				<Button label="Cancel" @click="open = false" />
				<Button
					variant="solid"
					theme="gray"
					type="submit"
					:label="series ? 'Save' : 'Create'"
					:loading="saving"
					:disabled="!form.title.trim()"
				/>
			</div>
		</form>
	</Dialog>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { Button, Dialog, ErrorMessage, FormControl, FormLabel, TextInput, vFocus } from 'frappe-ui'
import EmojiPicker from '@/components/EmojiPicker.vue'
import { errorMessage } from '@/lib/errors'
import type { VideoSeries } from '@/types'

type SeriesValues = { title: string; emoji: string; summary: string }

const props = defineProps<{
	/** Edit this series. Leave it out to create one. */
	series?: VideoSeries | null
	save: (values: SeriesValues) => Promise<unknown>
}>()

const open = defineModel<boolean>('open', { default: false })

const form = reactive<SeriesValues>({ title: '', emoji: '🎬', summary: '' })
const saving = ref(false)
const error = ref('')

// Fill the form each time the dialog opens, so Cancel drops the edits.
watch(open, (isOpen) => {
	if (!isOpen) return
	Object.assign(form, {
		title: props.series?.title ?? '',
		emoji: props.series?.emoji || '🎬',
		summary: props.series?.summary ?? '',
	})
	error.value = ''
})

async function submit() {
	saving.value = true
	error.value = ''
	try {
		await props.save({ ...form, title: form.title.trim() })
		open.value = false
	} catch (err) {
		error.value = errorMessage(err as Error)
	} finally {
		saving.value = false
	}
}
</script>
