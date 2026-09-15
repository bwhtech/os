<template>
	<SettingsPanel value="blog-notifications">
		<SettingsHeader title="Notifications">
			<template #actions>
				<Button
					variant="solid"
					theme="gray"
					label="Save"
					:loading="settings.setValue.loading"
					:disabled="!dirty"
					@click="save"
				/>
			</template>
		</SettingsHeader>
		<SettingsBody>
			<div class="flex flex-col gap-4 pt-3">
				<ErrorMessage :message="errorMessage(settings.error)" />
				<SettingsRow title="Email new comments" description="With a link to moderate.">
					<Switch v-model="draft.notify" />
				</SettingsRow>
				<TextInput v-if="draft.notify" v-model="draft.email" type="email" label="Send to" placeholder="Your email" />
			</div>
		</SettingsBody>
	</SettingsPanel>
</template>

<script setup lang="ts">
import { computed, reactive, watch } from 'vue'
import {
	Button,
	ErrorMessage,
	SettingsBody,
	SettingsHeader,
	SettingsPanel,
	SettingsRow,
	Switch,
	TextInput,
	toast,
	useDoc,
} from 'frappe-ui'
import { errorMessage } from '@/lib/errors'
import type { MailingSettings } from '@/types'

/** The Blog group of the Settings dialog. The fields live in Mailing Settings. See AppSettingsDialog. */
const props = defineProps<{ open: boolean }>()

const settings = useDoc<MailingSettings>({ doctype: 'Mailing Settings', name: 'Mailing Settings' })

const draft = reactive({ notify: false, email: '' })

const saved = computed(() => {
	const doc = settings.doc
	if (!doc) return null
	return { notify: Boolean(doc.notify_blog_comments), email: doc.blog_notification_email ?? '' }
})

const dirty = computed(() => Boolean(saved.value) && JSON.stringify(saved.value) !== JSON.stringify(draft))

// Start each opening from the saved values, so closing the dialog drops unsaved changes.
watch([() => props.open, saved], ([isOpen, value]) => isOpen && value && Object.assign(draft, value), {
	immediate: true,
})

async function save() {
	try {
		await settings.setValue.submit({
			notify_blog_comments: draft.notify ? 1 : 0,
			blog_notification_email: draft.email.trim() || null,
		})
		toast.success('Saved')
	} catch (error) {
		toast.error(errorMessage(error as Error))
	}
}
</script>
