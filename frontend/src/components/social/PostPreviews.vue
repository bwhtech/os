<template>
	<div class="space-y-6">
		<template v-for="target in targets" :key="target.result.channel">
			<XPreview
				v-if="target.result.provider === 'X'"
				:channel="target.channel"
				:parts="target.parts"
				:limit="target.result.limit"
				:errors="target.result.errors"
				:reply-settings="replySettings(target.settings)"
			/>
			<LinkedInPreview
				v-else
				:channel="target.channel"
				:parts="target.parts"
				:limit="target.result.limit"
				:errors="target.result.errors"
			/>
		</template>

		<p v-if="!targets.length" class="text-p-sm text-ink-gray-5">Pick a channel to see the post.</p>
	</div>
</template>

<script setup lang="ts">
import LinkedInPreview from '@/components/social/LinkedInPreview.vue'
import XPreview from '@/components/social/XPreview.vue'
import { settingsOf } from '@/lib/social'
import type { DraftPart } from '@/lib/social'
import type { SocialChannel, TargetValidation, XReplySettings } from '@/types'

/** The post as each picked platform would show it, with what that platform refuses. */
defineProps<{
	targets: {
		result: TargetValidation
		channel?: SocialChannel
		parts: DraftPart[]
		settings?: Record<string, unknown>
	}[]
}>()

function replySettings(settings?: Record<string, unknown>): XReplySettings {
	return (settingsOf(settings ?? null).reply_settings as XReplySettings) ?? 'everyone'
}
</script>
