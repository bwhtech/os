<template>
	<section class="space-y-4">
		<div class="space-y-1">
			<h2 class="text-lg-semibold text-ink-gray-8">Welcome Email</h2>
			<p class="text-p-sm text-ink-gray-5">
				Sent once, when a person joins. Leave the subject empty to send nothing.
			</p>
		</div>

		<TextInput v-model="subject" label="Subject" class="max-w-2xl" placeholder="Thanks for joining, {{ first_name }}" />
		<TextInput
			v-model="replyTo"
			type="email"
			label="Reply-to"
			class="max-w-2xl"
			placeholder="The address in Settings"
			description="Where a reply to this email goes."
		/>
		<EmailComposer
			ref="composer"
			v-model:content="content"
			v-model:theme="theme"
			:variables="WELCOME_VARIABLES"
		/>
	</section>
</template>

<script setup lang="ts">
import { useTemplateRef } from "vue";
import { TextInput } from "frappe-ui";
import EmailComposer from "@/components/email/EmailComposer.vue";
import { WELCOME_VARIABLES } from "@/lib/emailVariables";
import type { EmailDocument, NewsletterTheme } from "@/types";

const subject = defineModel<string>("subject", { required: true });
const replyTo = defineModel<string>("replyTo", { required: true });
const content = defineModel<EmailDocument | null>("content", { required: true });
const theme = defineModel<NewsletterTheme>("theme", { required: true });

const composer = useTemplateRef<InstanceType<typeof EmailComposer>>("composer");

defineExpose({
	getHtml: () => composer.value?.getHtml() ?? Promise.resolve(""),
});
</script>
