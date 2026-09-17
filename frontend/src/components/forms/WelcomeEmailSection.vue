<template>
	<section class="space-y-4">
		<div class="space-y-1">
			<h2 class="text-lg-semibold text-ink-gray-8">Welcome Email</h2>
			<p class="text-p-sm text-ink-gray-5">
				Sent once, when a new person signs up. Leave the subject empty to send nothing. With a
				lead magnet, link a button to
				<code v-pre class="font-mono text-ink-gray-7">{{ download_url }}</code>.
			</p>
		</div>

		<Select
			v-model="leadMagnet"
			class="max-w-2xl"
			label="Lead magnet"
			:description="leadMagnetDescription"
			placeholder="None"
			:options="leadMagnetOptions"
		/>
		<TextInput
			v-model="subject"
			label="Subject"
			class="max-w-2xl"
			placeholder="Here is your manual, {{ first_name }}"
			:required="Boolean(leadMagnet)"
		/>
		<TextInput
			v-model="replyTo"
			type="email"
			label="Reply-to"
			class="max-w-2xl"
			placeholder="The address in Settings"
			description="Where a reply to this email goes. A person who answers the welcome email is worth hearing."
		/>

		<!-- The save is refused without this link, and it is the one thing nobody can guess.
		     Better to say so while the email is being written, with the fix one click away. -->
		<div
			v-if="needsDownloadLink"
			class="flex flex-wrap items-center gap-3 rounded-6 bg-surface-amber-1 px-3 py-2.5"
		>
			<p class="text-p-sm text-ink-gray-7">
				This email gives away
				<span class="font-medium">{{ leadMagnetTitle }}</span>
				but has no download link, so it cannot be saved yet.
			</p>
			<Button class="ml-auto" label="Add download button" @click="addDownloadButton" />
		</div>

		<EmailComposer
			ref="composer"
			v-model:content="content"
			v-model:theme="theme"
			:variables="WELCOME_VARIABLES"
		/>
	</section>
</template>

<script setup lang="ts">
import { computed, useTemplateRef, watch } from "vue";
import { Button, Select, TextInput, useCall, useList } from "frappe-ui";
import EmailComposer from "@/components/email/EmailComposer.vue";
import { downloadButton } from "@/lib/emailStarters";
import { WELCOME_VARIABLES } from "@/lib/emailVariables";
import type { EmailDocument, LeadMagnet, NewsletterTheme } from "@/types";

const leadMagnet = defineModel<string>("leadMagnet", { required: true });
const subject = defineModel<string>("subject", { required: true });
const replyTo = defineModel<string>("replyTo", { required: true });
const content = defineModel<EmailDocument | null>("content", { required: true });
const theme = defineModel<NewsletterTheme>("theme", { required: true });

const composer = useTemplateRef<InstanceType<typeof EmailComposer>>("composer");

const leadMagnets = useList<LeadMagnet>({
	doctype: "Lead Magnet",
	fields: ["name", "title"],
	orderBy: "title asc",
	limit: 200,
});

const counts = useCall<Record<string, number>>({
	url: "/api/v2/method/bwh_os.mailing.api.get_download_counts",
});

const leadMagnetOptions = computed(() => [
	{ label: "None", value: "" },
	...(leadMagnets.data ?? []).map((item) => ({ label: item.title, value: item.name })),
]);

const leadMagnetDescription = computed(() => {
	if (!leadMagnet.value) return "The file people get in the welcome email.";
	const count = counts.data?.[leadMagnet.value] ?? 0;
	return `${count} ${count === 1 ? "subscriber has" : "subscribers have"} downloaded it, from all forms.`;
});

const leadMagnetTitle = computed(
	() => leadMagnets.data?.find((item) => item.name === leadMagnet.value)?.title ?? "a file",
);

/**
 * A form with a lead magnet has to hand the file over, and `{{ download_url }}` is the only
 * way to do it. The server refuses the save without it, so the page says so first. The token
 * cannot appear anywhere else in the document, so looking for the text is enough.
 */
const needsDownloadLink = computed(
	() => Boolean(leadMagnet.value) && !JSON.stringify(content.value ?? {}).includes("download_url"),
);

// Picking a file to give away is the moment the email needs a way to give it: the button
// goes in by itself, and the warning above is left for an email that loses it later.
watch(leadMagnet, (magnet) => {
	if (magnet && needsDownloadLink.value) addDownloadButton();
});

function addDownloadButton() {
	composer.value?.insertBlock(downloadButton());
}

defineExpose({
	getHtml: () => composer.value?.getHtml() ?? Promise.resolve(""),
});
</script>
