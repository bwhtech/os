<template>
	<Dialog :open="open" title="New Lead Magnet" @update:open="emit('update:open', $event)">
		<template #default="{ close }">
			<form class="space-y-4" @submit.prevent="submit">
				<TextInput
					v-model="title"
					label="Title"
					placeholder="The Missing Frappe Manual"
					required
					autofocus
				/>
				<LeadMagnetFileInput v-model="file" />

				<ErrorMessage :message="error" />

				<div class="flex justify-end gap-2 pt-2">
					<Button label="Cancel" @click="close" />
					<Button
						type="submit"
						variant="solid"
						theme="gray"
						label="Create Lead Magnet"
						:loading="saving"
						:disabled="!title.trim() || !file"
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
import LeadMagnetFileInput from '@/components/lead-magnets/LeadMagnetFileInput.vue'
import { errorMessage } from '@/lib/errors'
import type { LeadMagnet } from '@/types'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ 'update:open': [open: boolean] }>()

const router = useRouter()

const title = ref('')
const file = ref('')
const saving = ref(false)
const error = ref('')

watch(
	() => props.open,
	(open) => {
		if (!open) return
		title.value = ''
		file.value = ''
		error.value = ''
	},
)

async function submit() {
	saving.value = true
	error.value = ''
	try {
		const newDoc = useNewDoc<LeadMagnet>('Lead Magnet', {
			title: title.value.trim(),
			file: file.value,
		})
		const created = await newDoc.submit()
		emit('update:open', false)
		router.push(`/lead-magnets/${created.name}`)
	} catch (e) {
		error.value = errorMessage(e as Error)
	} finally {
		saving.value = false
	}
}
</script>
