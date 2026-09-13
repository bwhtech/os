<template>
	<Dialog :open="open" title="New Form" @update:open="emit('update:open', $event)">
		<template #default="{ close }">
			<form class="space-y-4" @submit.prevent="submit">
				<TextInput
					v-model="title"
					label="Title"
					placeholder="Blog post footer"
					required
					autofocus
				/>
				<TextInput
					v-model="formId"
					label="Form ID"
					description="Lowercase letters, digits, and hyphens. You cannot change it later."
					required
					@update:model-value="formIdEdited = true"
				/>

				<ErrorMessage :message="error" />

				<div class="flex justify-end gap-2 pt-2">
					<Button label="Cancel" @click="close" />
					<Button
						type="submit"
						variant="solid"
						theme="gray"
						label="Create Form"
						:loading="saving"
						:disabled="!title.trim() || !formId.trim()"
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
import { slugify } from '@/lib/slug'
import type { SignupForm } from '@/types'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ 'update:open': [open: boolean] }>()

const router = useRouter()

const title = ref('')
const formId = ref('')
/** Once the id is typed by hand, the title stops overwriting it. */
const formIdEdited = ref(false)
const saving = ref(false)
const error = ref('')

watch(title, (value) => {
	if (!formIdEdited.value) formId.value = slugify(value)
})

watch(
	() => props.open,
	(open) => {
		if (!open) return
		title.value = ''
		formId.value = ''
		formIdEdited.value = false
		error.value = ''
	},
)

async function submit() {
	saving.value = true
	error.value = ''
	try {
		const newDoc = useNewDoc<SignupForm>('Signup Form', {
			title: title.value.trim(),
			form_id: formId.value.trim(),
		})
		const created = await newDoc.submit()
		emit('update:open', false)
		router.push(`/forms/${created.name}`)
	} catch (e) {
		error.value = errorMessage(e as Error)
	} finally {
		saving.value = false
	}
}
</script>
