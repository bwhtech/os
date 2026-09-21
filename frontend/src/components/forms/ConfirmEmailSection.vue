<template>
	<div class="space-y-4">
		<TextInput v-model="subject" label="Subject" required class="max-w-2xl" />
		<TextInput
			v-model="replyTo"
			type="email"
			label="Reply-to"
			placeholder="The address in Settings"
			description="Where a reply to this email goes."
			class="max-w-2xl"
		/>
		<EmailComposer
			ref="composer"
			v-model:content="content"
			v-model:theme="theme"
			:variables="CONFIRM_VARIABLES"
		/>
		<p class="text-p-sm text-ink-gray-5">
			Link a button to <code v-pre class="font-mono text-ink-gray-7">{{ confirm_url }}</code>.
			The email cannot be saved without it.
		</p>
	</div>
</template>

<script setup lang="ts">
import { useTemplateRef } from 'vue'
import { TextInput } from 'frappe-ui'
import EmailComposer from '@/components/email/EmailComposer.vue'
import { CONFIRM_VARIABLES } from '@/lib/emailVariables'
import type { EmailDocument, NewsletterTheme } from '@/types'

const subject = defineModel<string>('subject', { required: true })
const replyTo = defineModel<string>('replyTo', { required: true })
const content = defineModel<EmailDocument | null>('content', { required: true })
const theme = defineModel<NewsletterTheme>('theme', { required: true })

const composer = useTemplateRef<InstanceType<typeof EmailComposer>>('composer')

defineExpose({
	getHtml: () => composer.value?.getHtml() ?? Promise.resolve(''),
})
</script>
