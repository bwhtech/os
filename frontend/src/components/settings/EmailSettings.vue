<template>
	<SettingsPanel value="sending">
		<SettingsHeader title="Sending" description="The account that sends every list email.">
			<template #actions>
				<SaveButton />
			</template>
		</SettingsHeader>
		<SettingsBody>
			<ErrorMessage :message="errorMessage(settings.error)" />
			<div class="flex flex-col gap-4">
				<Select
					v-model="draft.emailAccount"
					label="Email Account"
					placeholder="Default outgoing account"
					:options="accountOptions"
					description="Only accounts with outgoing email on. Set up accounts in the desk."
				/>
				<TextInput
					v-model.number="draft.defaultHourlyLimit"
					type="number"
					:min="1"
					label="Default hourly limit"
					description="Most newsletter emails per hour. New newsletters copy this value."
				/>
				<p class="text-p-sm text-ink-gray-5">
					From address:
					<span class="text-ink-gray-7">{{ senderAddress || 'the default outgoing account' }}</span>
				</p>
			</div>
		</SettingsBody>
	</SettingsPanel>

	<SettingsPanel value="footer">
		<SettingsHeader title="Footer" description="Shown at the bottom of every list email.">
			<template #actions>
				<SaveButton />
			</template>
		</SettingsHeader>
		<SettingsBody>
			<ErrorMessage :message="errorMessage(settings.error)" />
			<div class="flex flex-col gap-4">
				<TextInput v-model="draft.companyName" label="Company name" />
				<TextInput v-model="draft.gstin" label="GSTIN" />
				<Textarea v-model="draft.postalAddress" label="Postal address" :rows="3" />
			</div>
		</SettingsBody>
	</SettingsPanel>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, reactive, watch } from 'vue'
import {
	Button,
	ErrorMessage,
	Select,
	SettingsBody,
	SettingsHeader,
	SettingsPanel,
	TextInput,
	Textarea,
	toast,
	useDoc,
	useList,
} from 'frappe-ui'
import { errorMessage } from '@/lib/errors'
import type { MailingSettings } from '@/types'

/** The Email group of the Settings dialog. Its panels edit Mailing Settings. See AppSettingsDialog. */
const props = defineProps<{ open: boolean }>()

const settings = useDoc<MailingSettings>({ doctype: 'Mailing Settings', name: 'Mailing Settings' })

const accounts = useList<{ name: string; email_id: string }>({
	doctype: 'Email Account',
	fields: ['name', 'email_id'],
	filters: { enable_outgoing: 1 },
	limit: 100,
})

const accountOptions = computed(() => [
	{ label: 'Default outgoing account', value: '' },
	...(accounts.data ?? []).map((account) => ({
		label: `${account.name} (${account.email_id})`,
		value: account.name,
	})),
])

const senderAddress = computed(
	() => accounts.data?.find((account) => account.name === draft.emailAccount)?.email_id,
)

const draft = reactive({
	emailAccount: '',
	defaultHourlyLimit: 500,
	companyName: '',
	gstin: '',
	postalAddress: '',
})

const saved = computed(() => {
	const doc = settings.doc
	if (!doc) return null
	return {
		emailAccount: doc.email_account ?? '',
		defaultHourlyLimit: doc.default_hourly_limit,
		companyName: doc.company_name ?? '',
		gstin: doc.gstin ?? '',
		postalAddress: doc.postal_address ?? '',
	}
})

const dirty = computed(
	() => Boolean(saved.value) && JSON.stringify(saved.value) !== JSON.stringify(draft),
)

// Start each opening from the saved values, so closing the dialog drops unsaved changes.
watch([() => props.open, saved], ([isOpen, value]) => isOpen && value && Object.assign(draft, value), {
	immediate: true,
})

async function save() {
	try {
		await settings.setValue.submit({
			email_account: draft.emailAccount || null,
			default_hourly_limit: draft.defaultHourlyLimit,
			company_name: draft.companyName,
			gstin: draft.gstin,
			postal_address: draft.postalAddress,
		})
		toast.success('Email settings saved')
	} catch (error) {
		toast.error(errorMessage(error as Error))
	}
}

/** One Save for both panels, because they edit the same document. */
const SaveButton = defineComponent(() => () =>
	h(Button, {
		variant: 'solid',
		theme: 'gray',
		label: 'Save',
		loading: settings.setValue.loading,
		disabled: !dirty.value,
		onClick: save,
	}),
)
</script>
