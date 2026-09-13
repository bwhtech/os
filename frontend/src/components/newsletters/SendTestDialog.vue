<template>
	<Dialog :open="open" title="Send Test" @update:open="emit('update:open', $event)">
		<template #default="{ close }">
			<form class="space-y-4" @submit.prevent="submit(close)">
				<TextInput
					v-model="email"
					type="email"
					label="Email"
					description="Unsaved changes are saved first. The subject starts with [Test]."
					required
					autofocus
				/>

				<ErrorMessage :message="errorMessage(sendTest.error)" />

				<div class="flex justify-end gap-2 pt-2">
					<Button label="Cancel" @click="close" />
					<Button
						type="submit"
						variant="solid"
						theme="gray"
						label="Send Test"
						:loading="sendTest.loading || saving"
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
import { useSession } from '@/composables/useSession'
import { errorMessage } from '@/lib/errors'

const props = defineProps<{
	open: boolean
	issueId: string
	/** Saves unsaved changes. Resolves false when the save failed. */
	save: () => Promise<boolean>
}>()
const emit = defineEmits<{ 'update:open': [open: boolean] }>()

const { user } = useSession()

const email = ref('')
const saving = ref(false)

const sendTest = useCall<string, { issue: string; email: string }>({
	url: '/api/v2/method/bwh_os.mailing.api.send_test_newsletter',
	method: 'POST',
	immediate: false,
})

// Keep the last address between sends. Start with the user's own address.
watch(
	() => props.open,
	(open) => {
		if (!open) return
		email.value ||= user.value?.email ?? ''
		sendTest.reset()
	},
)

async function submit(close: () => void) {
	saving.value = true
	const saved = await props.save()
	saving.value = false
	if (!saved) return

	const recipient = await sendTest.submit({ issue: props.issueId, email: email.value })
	if (!recipient) return
	toast.success(`Test sent to ${recipient}`)
	close()
}
</script>
