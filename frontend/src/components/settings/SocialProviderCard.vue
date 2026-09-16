<template>
	<div class="rounded-6 border border-outline-gray-2">
		<div class="flex items-center gap-3 px-4 py-3">
			<PlatformIcon :provider="app.provider" class="size-5 shrink-0 text-ink-gray-7" />
			<div class="min-w-0 flex-1">
				<p class="text-base font-medium text-ink-gray-8">{{ app.provider }}</p>
				<p class="truncate text-p-sm text-ink-gray-5">{{ summary }}</p>
			</div>
			<Badge v-if="channel" :theme="statusTheme" :label="channel.status" />
			<Button
				:label="credentialsOpen ? 'Hide setup' : 'Setup'"
				variant="ghost"
				@click="credentialsOpen = !credentialsOpen"
			/>
			<Button
				v-if="connectLabel"
				variant="solid"
				theme="gray"
				:label="connectLabel"
				:loading="connect.loading"
				:disabled="!app.has_credentials"
				:tooltip="app.has_credentials ? undefined : 'Add the client id and secret first'"
				@click="startConnect"
			/>
		</div>

		<div v-if="channel" class="flex items-center gap-3 border-t border-outline-gray-2 px-4 py-3">
			<Avatar :image="channel.avatar_url ?? undefined" :label="channel.display_name ?? app.provider" size="lg" />
			<div class="min-w-0 flex-1">
				<p class="truncate text-base text-ink-gray-8">{{ channel.display_name }}</p>
				<p class="truncate text-p-sm text-ink-gray-5">{{ expiry }}</p>
			</div>
			<Button
				v-if="channel.status !== 'Disconnected'"
				label="Disconnect"
				:loading="disconnect.loading"
				@click="askDisconnect"
			/>
		</div>

		<p v-if="channel?.last_error" class="border-t border-outline-gray-2 px-4 py-3 text-p-sm text-ink-red-3">
			{{ channel.last_error }}
		</p>

		<div v-if="credentialsOpen" class="flex flex-col gap-4 border-t border-outline-gray-2 px-4 py-4">
			<div>
				<p class="mb-1.5 text-p-sm text-ink-gray-5">Redirect URI</p>
				<div class="flex items-center gap-2">
					<!-- The URI is one long word, and the settings body sizes itself to its
					     content. `w-0` keeps the URI out of that measurement, `flex-1` still
					     fills the row, and the scroll area shows the rest on a swipe. -->
					<ScrollArea
						orientation="horizontal"
						class="w-0 flex-1 rounded-4 bg-surface-gray-2"
						viewport-class="px-2 py-1.5"
					>
						<code class="whitespace-nowrap text-p-sm text-ink-gray-7">{{ app.redirect_uri }}</code>
					</ScrollArea>
					<Button icon="lucide-copy" aria-label="Copy redirect URI" @click="copy(app.redirect_uri)" />
				</div>
				<p class="mt-1.5 text-p-sm text-ink-gray-5">Register this in the {{ app.provider }} app console.</p>
			</div>
			<div>
				<p class="mb-1.5 text-p-sm text-ink-gray-5">Scopes</p>
				<p class="text-p-sm text-ink-gray-7">{{ app.scopes.join(' ') }}</p>
			</div>
			<TextInput v-model="draft.clientId" label="Client ID" />
			<TextInput
				v-model="draft.clientSecret"
				type="password"
				label="Client secret"
				:placeholder="app.has_credentials ? 'Saved. Type to replace it.' : ''"
			/>
			<ErrorMessage :message="errorMessage(save.error)" />
			<div class="flex justify-end">
				<Button
					variant="solid"
					theme="gray"
					label="Save"
					:loading="save.loading"
					:disabled="!dirty"
					@click="submit"
				/>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import {
	Avatar,
	Badge,
	Button,
	ErrorMessage,
	ScrollArea,
	TextInput,
	dayjs,
	dialog,
	toast,
	useCall,
} from 'frappe-ui'
import PlatformIcon from '@/components/social/PlatformIcon.vue'
import { errorMessage } from '@/lib/errors'
import type { SocialChannel, SocialProviderApp } from '@/types'

/** One platform in the Social Channels panel: its credentials, and the account it connected. */
const props = defineProps<{ app: SocialProviderApp; channel?: SocialChannel }>()
const emit = defineEmits<{ saved: [] }>()

const credentialsOpen = ref(false)
const draft = reactive({ clientId: '', clientSecret: '' })

const save = useCall<void, { provider: string; client_id: string; client_secret: string }>({
	url: '/api/v2/method/bwh_os.social.api.set_credentials',
	method: 'POST',
	immediate: false,
})

const connect = useCall<string, { provider: string }>({
	url: '/api/v2/method/bwh_os.social.api.connect_channel',
	method: 'POST',
	immediate: false,
})

const disconnect = useCall<void, { channel: string }>({
	url: '/api/v2/method/bwh_os.social.api.disconnect_channel',
	method: 'POST',
	immediate: false,
})

const connectLabel = computed(() => {
	if (!props.channel) return 'Connect'
	return props.channel.status === 'Connected' ? '' : 'Reconnect'
})

const summary = computed(() => {
	const channel = props.channel
	if (!channel) return props.app.has_credentials ? 'Ready to connect' : 'Add the client id and secret'
	if (channel.status === 'Expired') return 'The token has run out'
	if (channel.status === 'Disconnected') return 'Connect again to post'
	return channel.handle ? `@${channel.handle}` : 'Connected'
})

const statusTheme = computed(() => {
	if (props.channel?.status === 'Connected') return 'green'
	return props.channel?.status === 'Expired' ? 'red' : 'gray'
})

const expiry = computed(() => {
	const channel = props.channel
	if (!channel || channel.status === 'Disconnected') return 'The OS holds no token for it'
	if (!channel.expires_on) return 'The token does not expire'
	const left = channel.days_left ?? 0
	if (left <= 0) return `The token expired ${dayjs(channel.expires_on).fromNow()}`
	return `The token expires in ${left} ${left === 1 ? 'day' : 'days'}`
})

const dirty = computed(
	() => draft.clientId.trim() !== (props.app.client_id ?? '') || Boolean(draft.clientSecret),
)

// A secret never comes back from the server, so the field starts empty every time.
watch(
	() => props.app.client_id,
	(clientId) => {
		draft.clientId = clientId ?? ''
		draft.clientSecret = ''
	},
	{ immediate: true },
)

async function startConnect() {
	try {
		const url = await connect.submit({ provider: props.app.provider })
		// The platform takes over the tab. It comes back to /os/social when it is done.
		if (url) window.location.href = url
	} catch (error) {
		toast.error(errorMessage(error as Error))
	}
}

function askDisconnect() {
	if (!props.channel) return
	const name = props.channel.display_name ?? props.app.provider
	dialog.danger({
		title: `Disconnect ${props.app.provider}`,
		message: `The OS drops the token of ${name} and stops posting for it. Scheduled posts fail until you connect again.`,
		confirmLabel: 'Disconnect',
		onConfirm: async () => {
			try {
				await disconnect.submit({ channel: props.channel!.name })
				toast.success('Disconnected')
				emit('saved')
			} catch (error) {
				toast.error(errorMessage(error as Error))
			}
		},
	})
}

async function copy(text: string) {
	await navigator.clipboard.writeText(text)
	toast.success('Copied')
}

async function submit() {
	try {
		await save.submit({
			provider: props.app.provider,
			client_id: draft.clientId.trim(),
			client_secret: draft.clientSecret,
		})
		draft.clientSecret = ''
		toast.success('Saved')
		emit('saved')
	} catch (error) {
		toast.error(errorMessage(error as Error))
	}
}
</script>
