<template>
	<div class="flex flex-wrap items-center gap-2">
		<button
			v-for="channel in channels"
			:key="channel.name"
			type="button"
			role="switch"
			:aria-checked="picked.includes(channel.name)"
			:disabled="disabled || channel.status !== 'Connected'"
			:title="tooltip(channel)"
			:class="[
				'flex items-center gap-2 rounded-full border py-1 pl-1 pr-3 transition-colors',
				picked.includes(channel.name)
					? 'border-outline-gray-3 bg-surface-gray-2'
					: 'border-outline-gray-2 bg-surface-white',
				disabled || channel.status !== 'Connected'
					? 'cursor-not-allowed opacity-50'
					: 'hover:border-outline-gray-3',
			]"
			@click="toggle(channel)"
		>
			<span class="relative">
				<Avatar :image="channel.avatar_url ?? undefined" :label="label(channel)" size="sm" />
				<!-- The dot is the channel, not the post: a token that died shows here first. -->
				<span
					v-if="channel.status !== 'Connected'"
					class="absolute -bottom-0.5 -right-0.5 size-2 rounded-full bg-surface-red-5 ring-2 ring-surface-white"
					aria-hidden="true"
				/>
			</span>
			<PlatformIcon :provider="channel.provider" class="size-3.5 text-ink-gray-7" />
			<span class="text-p-sm text-ink-gray-8">{{ label(channel) }}</span>
		</button>

		<p v-if="!channels.length" class="text-p-sm text-ink-gray-5">
			No channels yet. Connect LinkedIn or X in Settings.
		</p>
	</div>
</template>

<script setup lang="ts">
import { Avatar } from 'frappe-ui'
import PlatformIcon from '@/components/social/PlatformIcon.vue'
import type { SocialChannel } from '@/types'

/** Which channels a post goes to. An expired channel cannot be picked until it reconnects. */
const props = defineProps<{ channels: SocialChannel[]; disabled?: boolean }>()

const picked = defineModel<string[]>({ required: true })

function toggle(channel: SocialChannel) {
	if (props.disabled || channel.status !== 'Connected') return
	picked.value = picked.value.includes(channel.name)
		? picked.value.filter((name) => name !== channel.name)
		: [...picked.value, channel.name]
}

function label(channel: SocialChannel): string {
	return channel.display_name ?? channel.handle ?? channel.provider
}

function tooltip(channel: SocialChannel): string | undefined {
	if (channel.status === 'Connected') return undefined
	return `${channel.provider} is ${channel.status.toLowerCase()}. Connect it again in Settings.`
}
</script>
