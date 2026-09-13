<template>
	<Dialog :open="open" title="Add Subscriber" @update:open="emit('update:open', $event)">
		<template #default="{ close }">
			<form class="space-y-4" @submit.prevent="submit(close)">
				<TextInput v-model="email" type="email" label="Email" required autofocus />
				<TextInput v-model="firstName" label="First Name" />
				<TagPicker v-model="tags" />

				<ErrorMessage :message="errorMessage" />

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
import { computed, ref, watch } from 'vue'
import { Button, Dialog, ErrorMessage, FrappeResponseError, TextInput, toast, useCall } from 'frappe-ui'
import TagPicker from '@/components/subscribers/TagPicker.vue'

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

// frappe-ui prefixes the message with the exception type, e.g. "DuplicateEntryError: ".
const errorMessage = computed(() => {
	const error = addSubscriber.error
	if (!error) return ''
	if (!(error instanceof FrappeResponseError)) return error.message
	return error.message.replace(`${error.type}: `, '')
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
