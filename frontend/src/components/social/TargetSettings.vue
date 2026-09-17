<template>
	<div v-if="provider === 'X'" class="flex flex-wrap items-center gap-x-2 gap-y-3">
		<Avatar :image="channel?.avatar_url ?? undefined" :label="label" size="sm" />
		<p class="text-p-sm text-ink-gray-7">{{ label }}</p>
		<FormControl
			class="ml-auto"
			type="select"
			size="sm"
			label="Who can reply"
			:options="REPLY_OPTIONS"
			:model-value="replySettings"
			:disabled="disabled"
			@update:model-value="emit('update:modelValue', { ...settings, reply_settings: $event })"
		/>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Avatar, FormControl } from 'frappe-ui'
import { REPLY_OPTIONS, settingsOf } from '@/lib/social'
import type { SocialChannel, SocialProvider, XReplySettings } from '@/types'

/**
 * What one channel needs beyond the text. Only X has anything to ask so far, so every
 * other platform draws nothing here.
 */
const props = defineProps<{
	provider: SocialProvider
	channel?: SocialChannel
	/** The `settings` of the target, which the server keeps as JSON */
	modelValue: string | Record<string, unknown> | null
	disabled?: boolean
}>()

const emit = defineEmits<{ 'update:modelValue': [settings: Record<string, unknown>] }>()

const label = computed(() => props.channel?.display_name ?? props.provider)
const settings = computed(() => settingsOf(props.modelValue))
const replySettings = computed<XReplySettings>(
	() => (settings.value.reply_settings as XReplySettings) ?? 'everyone',
)
</script>
