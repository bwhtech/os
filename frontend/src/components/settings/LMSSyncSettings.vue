<template>
	<SettingsPanel value="lms-sync">
		<SettingsHeader title="LMS Sync" description="Adds new LMS users to the list.">
			<template #actions>
				<Button
					label="Sync now"
					icon-left="lucide-refresh-cw"
					:loading="syncNow.loading"
					:disabled="dirty || !canSync"
					:tooltip="dirty ? 'Save first' : undefined"
					@click="sync"
				/>
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
			<ErrorMessage :message="errorMessage(settings.error)" />
			<div class="flex flex-col gap-4">
				<Switch
					v-model="draft.enabled"
					label="Sync every day"
					description="New users join as Active, with no welcome email. People already on the list stay as they are."
				/>
				<TextInput v-model="draft.siteUrl" type="url" label="Site URL" placeholder="https://school.bwh.tech" />
				<TextInput
					v-model="draft.apiKey"
					label="API key"
					description="Of an LMS user that can read User and LMS Batch Enrollment."
				/>
				<TextInput v-model="draft.apiSecret" type="password" label="API secret" />
				<TagPicker
					v-model="draft.userTags"
					label="Tags for new users"
					description="Added to each LMS user that joins the list."
				/>
				<TagPicker
					v-model="draft.enrollmentTags"
					label="Tags for enrollees"
					description="Added to subscribers who enroll in an LMS batch. Tags are never removed."
				/>
				<p v-if="settings.doc?.last_synced_on" class="text-p-sm text-ink-gray-5">
					Last sync {{ dayjs(settings.doc.last_synced_on).fromNow() }}:
					<span :class="settings.doc.last_sync_status === 'Failed' ? 'text-ink-red-4' : 'text-ink-gray-7'">
						{{ settings.doc.last_sync_message }}
					</span>
				</p>
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
	Switch,
	TextInput,
	dayjs,
	toast,
	useCall,
	useDoc,
} from 'frappe-ui'
import TagPicker from '@/components/tags/TagPicker.vue'
import { errorMessage } from '@/lib/errors'
import type { LMSSyncResult, LMSSyncSettings } from '@/types'

/** The LMS Sync panel of the Settings dialog. See bwh_os.mailing.lms_sync. */
const props = defineProps<{ open: boolean }>()

const settings = useDoc<LMSSyncSettings>({ doctype: 'LMS Sync Settings', name: 'LMS Sync Settings' })

const syncNow = useCall<LMSSyncResult>({
	url: '/api/v2/method/bwh_os.mailing.api.sync_lms_now',
	method: 'POST',
	immediate: false,
	onError: (error) => toast.error(errorMessage(error)),
})

const draft = reactive({
	enabled: false,
	siteUrl: '',
	apiKey: '',
	// Frappe sends a saved secret as asterisks and ignores them on save.
	apiSecret: '',
	userTags: [] as string[],
	enrollmentTags: [] as string[],
})

const saved = computed(() => {
	const doc = settings.doc
	if (!doc) return null
	return {
		enabled: Boolean(doc.enabled),
		siteUrl: doc.site_url ?? '',
		apiKey: doc.api_key ?? '',
		apiSecret: doc.api_secret ?? '',
		userTags: doc.user_tags.map((row) => row.tag),
		enrollmentTags: doc.enrollment_tags.map((row) => row.tag),
	}
})

const dirty = computed(() => Boolean(saved.value) && JSON.stringify(saved.value) !== JSON.stringify(draft))

const canSync = computed(() => Boolean(saved.value?.siteUrl && saved.value.apiKey && saved.value.apiSecret))

// Start each opening from the saved values, so closing the dialog drops unsaved changes.
watch([() => props.open, saved], ([isOpen, value]) => isOpen && value && Object.assign(draft, value), {
	immediate: true,
})

async function save() {
	try {
		await settings.setValue.submit({
			enabled: draft.enabled ? 1 : 0,
			site_url: draft.siteUrl.trim() || null,
			api_key: draft.apiKey.trim() || null,
			api_secret: draft.apiSecret || null,
			user_tags: draft.userTags.map((tag) => ({ tag })),
			enrollment_tags: draft.enrollmentTags.map((tag) => ({ tag })),
		})
		toast.success('LMS sync saved')
	} catch (error) {
		toast.error(errorMessage(error as Error))
	}
}

async function sync() {
	const result = await syncNow.submit()
	settings.reload()
	if (!result) return
	if (result.status === 'Failed') toast.error(result.message)
	else toast.success(result.message)
}
</script>
