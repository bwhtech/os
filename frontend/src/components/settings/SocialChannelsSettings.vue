<template>
	<SettingsPanel value="social-channels">
		<SettingsHeader title="Channels" />
		<SettingsBody>
			<div class="flex flex-col gap-4 pt-3">
				<p class="text-p-sm text-ink-gray-5">
					Make an app in each platform console, paste its client id and secret here, then connect the
					account that posts.
				</p>
				<ErrorMessage :message="errorMessage(apps.error)" />
				<SocialProviderCard
					v-for="app in apps.data ?? []"
					:key="app.provider"
					:app="app"
					:channel="channelOf(app.provider)"
					@saved="reload"
				/>
			</div>
		</SettingsBody>
	</SettingsPanel>
</template>

<script setup lang="ts">
import { watch } from 'vue'
import { ErrorMessage, SettingsBody, SettingsHeader, SettingsPanel, useCall } from 'frappe-ui'
import SocialProviderCard from '@/components/settings/SocialProviderCard.vue'
import { errorMessage } from '@/lib/errors'
import type { SocialChannel, SocialProvider, SocialProviderApp } from '@/types'

/** The Social group of the Settings dialog. See bwh_os/social/oauth_apps.py. */
const props = defineProps<{ open: boolean }>()

const apps = useCall<SocialProviderApp[]>({
	url: '/api/v2/method/bwh_os.social.api.get_provider_apps',
	method: 'GET',
	immediate: false,
	cacheKey: 'social-provider-apps',
})

const channels = useCall<SocialChannel[]>({
	url: '/api/v2/method/bwh_os.social.api.get_channels',
	method: 'GET',
	immediate: false,
	cacheKey: 'social-channels',
})

// The panel reads once per opening, so a connect made in another tab shows up.
watch(() => props.open, (isOpen) => isOpen && reload(), { immediate: true })

function channelOf(provider: SocialProvider) {
	return channels.data?.find((channel) => channel.provider === provider)
}

function reload() {
	apps.submit()
	channels.submit()
}
</script>
