<template>
	<section class="space-y-4">
		<div class="space-y-1">
			<h2 class="text-lg-semibold text-ink-gray-8">Delivery Email</h2>
			<p class="text-p-sm text-ink-gray-5">
				Sent on signup, from Send to…, or with a newsletter. Link a button to
				<code v-pre class="font-mono text-ink-gray-7">{{ download_url }}</code>.
			</p>
		</div>

		<TextInput v-model="subject" label="Subject" class="max-w-2xl" placeholder="Here is your copy, {{ first_name }}" />
		<TextInput
			v-model="replyTo"
			type="email"
			label="Reply-to"
			class="max-w-2xl"
			placeholder="The address in Settings"
			description="Where a reply to this email goes."
		/>

		<!-- The save is refused without this link, and it is the one thing nobody can guess.
		     Better to say so while the email is being written, with the fix one click away. -->
		<div
			v-if="needsDownloadLink"
			class="flex flex-wrap items-center gap-3 rounded-6 bg-surface-amber-1 px-3 py-2.5"
		>
			<p class="text-p-sm text-ink-gray-7">
				A subject is set but the email has no download link, so it cannot be saved yet.
			</p>
			<Button class="ml-auto" label="Add download button" @click="addDownloadButton" />
		</div>

		<EmailComposer
			ref="composer"
			v-model:content="content"
			v-model:theme="theme"
			:variables="LEAD_MAGNET_VARIABLES"
		/>
	</section>
</template>

<script setup lang="ts">
import { computed, useTemplateRef } from "vue";
import { Button, TextInput } from "frappe-ui";
import EmailComposer from "@/components/email/EmailComposer.vue";
import { downloadButton } from "@/lib/emailStarters";
import { LEAD_MAGNET_VARIABLES } from "@/lib/emailVariables";
import type { EmailDocument, NewsletterTheme } from "@/types";

const subject = defineModel<string>("subject", { required: true });
const replyTo = defineModel<string>("replyTo", { required: true });
const content = defineModel<EmailDocument | null>("content", { required: true });
const theme = defineModel<NewsletterTheme>("theme", { required: true });

const composer = useTemplateRef<InstanceType<typeof EmailComposer>>("composer");

/**
 * A subject with no `{{ download_url }}` cannot be saved. The token cannot appear anywhere
 * else in the document, so looking for the text is enough.
 */
const needsDownloadLink = computed(
	() => Boolean(subject.value) && !JSON.stringify(content.value ?? {}).includes("download_url"),
);

function addDownloadButton() {
	composer.value?.insertBlock(downloadButton());
}

defineExpose({
	getHtml: () => composer.value?.getHtml() ?? Promise.resolve(""),
});
</script>
