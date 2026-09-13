<template>
	<Dialog :open="open" title="Add Subscriber" @update:open="emit('update:open', $event)">
		<template #default="{ close }">
			<form class="space-y-4" @submit.prevent="submit(close)">
				<TextInput v-model="email" type="email" label="Email" required autofocus />
				<TextInput v-model="firstName" label="First Name" />
				<TagPicker v-model="tags" />

				<ErrorMessage :message="errorMessage(addSubscriber.error)" />

				<div class="flex justify-end gap-2 pt-2">
					<Button label="Cancel" @click="close" />
					<Button
						type="submit"
						variant="solid"
						theme="gray"
						label="Add"
						:loading="addSubscriber.loading"
						:disabled="!email.trim()"
					/>
				</div>
			</form>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Button, Dialog, ErrorMessage, TextInput, toast, useCall } from 'frappe-ui'
import TagPicker from '@/components/tags/TagPicker.vue'
import { errorMessage } from '@/lib/errors'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ 'update:open': [open: boolean]; created: [name: string] }>()

const email = ref('')
const firstName = ref('')
const tags = ref<string[]>([])

const addSubscriber = useCall<string, { email: string; first_name: string; tags: string[] }>({
	url: '/api/v2/method/bwh_os.mailing.api.add_subscriber',
	method: 'POST',
	immediate: false,
})

// Start each opening with an empty form.
watch(
	() => props.open,
	(open) => {
		if (!open) return
		email.value = ''
		firstName.value = ''
		tags.value = []
		addSubscriber.reset()
	},
)

async function submit(close: () => void) {
	const name = await addSubscriber.submit({
		email: email.value,
		first_name: firstName.value,
		tags: tags.value,
	})
	if (!name) return
	toast.success(`${name} added`)
	emit('created', name)
	close()
}
</script>
