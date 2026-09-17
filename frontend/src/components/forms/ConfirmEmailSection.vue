<template>
	<section class="space-y-4">
		<div class="space-y-1">
			<h2 class="text-lg-semibold text-ink-gray-8">Confirm Email</h2>
			<p class="text-p-sm text-ink-gray-5">
				Sent when a person signs up. The person stays Pending, and gets the welcome email
				only after they confirm. Link a button to
				<code v-pre class="font-mono text-ink-gray-7">{{ confirm_url }}</code>.
			</p>
		</div>

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
	</section>
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
