<template>
	<Dialog :open="open" title="New Newsletter" @update:open="emit('update:open', $event)">
		<template #default="{ close }">
			<form class="space-y-4" @submit.prevent="submit">
				<TextInput v-model="subject" label="Subject" required autofocus />

				<ErrorMessage :message="error" />

				<div class="flex justify-end gap-2 pt-2">
					<Button label="Cancel" @click="close" />
					<Button
						type="submit"
						variant="solid"
						theme="gray"
						label="Create Draft"
						:loading="saving"
						:disabled="!subject.trim()"
					/>
				</div>
			</form>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Button, Dialog, ErrorMessage, TextInput, useNewDoc } from 'frappe-ui'
import { errorMessage } from '@/lib/errors'
import type { NewsletterIssue } from '@/types'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ 'update:open': [open: boolean] }>()

const router = useRouter()

const subject = ref('')
const saving = ref(false)
const error = ref('')

watch(
	() => props.open,
	(open) => {
		if (!open) return
		subject.value = ''
		error.value = ''
	},
)

async function submit() {
	saving.value = true
	error.value = ''
	try {
		const newDoc = useNewDoc<NewsletterIssue>('Newsletter Issue', { subject: subject.value.trim() })
		const created = await newDoc.submit()
		emit('update:open', false)
		router.push(`/newsletters/${created.name}`)
	} catch (e) {
		error.value = errorMessage(e as Error)
	} finally {
		saving.value = false
	}
}
</script>
