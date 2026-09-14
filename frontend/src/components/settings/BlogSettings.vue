<template>
	<SettingsPanel value="blog-comments">
		<SettingsHeader
			title="Comments"
			description="The Turso database of the blog. OS reads and changes comments in it live."
		>
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
			<ErrorMessage :message="errorMessage(settings.error)" />
			<div class="flex flex-col gap-4">
				<TextInput
					v-model="draft.url"
					label="Turso URL"
					placeholder="libsql://bwhtech-blog-prod-....turso.io"
					description="Use the dev database on a dev site."
				/>
				<Password
					v-model="draft.token"
					label="Turso token"
					:placeholder="hasToken ? 'Saved. Enter a new token to replace it.' : ''"
					description="A full-access token made for OS only: turso db tokens create <database>"
				/>
				<div class="flex items-center gap-3">
					<Button
						label="Test connection"
						icon-left="lucide-plug"
						:loading="connection.loading"
						:disabled="dirty || !settings.doc?.turso_url || !hasToken"
						@click="connection.submit()"
					/>
					<p v-if="dirty" class="text-p-sm text-ink-gray-5">Save to test the new values.</p>
					<p v-else-if="connection.error" class="text-p-sm text-ink-red-7">
						{{ errorMessage(connection.error) }}
					</p>
					<p v-else-if="connection.data" class="text-p-sm text-ink-green-7">
						Connected to {{ connection.data }}
					</p>
				</div>
			</div>
		</SettingsBody>
	</SettingsPanel>
</template>

<script setup lang="ts">
import { computed, reactive, watch } from 'vue'
import {
	Button,
	ErrorMessage,
	Password,
	SettingsBody,
	SettingsHeader,
	SettingsPanel,
	TextInput,
	toast,
	useCall,
	useDoc,
} from 'frappe-ui'
import { errorMessage } from '@/lib/errors'
import type { BlogSettings } from '@/types'

/** The Blog group of the Settings dialog. See AppSettingsDialog. */
const props = defineProps<{ open: boolean }>()

const settings = useDoc<BlogSettings>({ doctype: 'Blog Settings', name: 'Blog Settings' })

const connection = useCall<string>({
	url: '/api/v2/method/bwh_os.blog.api.test_connection',
	method: 'POST',
	immediate: false,
})

// The token never comes back from the server, so an empty draft token keeps the saved one.
const draft = reactive({ url: '', token: '' })

const hasToken = computed(() => Boolean(settings.doc?.turso_token))
const dirty = computed(() => draft.url !== (settings.doc?.turso_url ?? '') || Boolean(draft.token))

watch(
	[() => props.open, () => settings.doc],
	([isOpen, doc]) => {
		if (!isOpen || !doc) return
		draft.url = doc.turso_url ?? ''
		draft.token = ''
		connection.reset()
	},
	{ immediate: true },
)

async function save() {
	try {
		await settings.setValue.submit({
			turso_url: draft.url,
			...(draft.token ? { turso_token: draft.token } : {}),
		})
		draft.token = ''
		toast.success('Blog settings saved')
	} catch (error) {
		toast.error(errorMessage(error as Error))
	}
}
</script>
