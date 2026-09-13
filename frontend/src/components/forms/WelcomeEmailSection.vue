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

		<EmailComposer
			ref="composer"
			v-model:content="content"
			v-model:theme="theme"
			:variables="WELCOME_VARIABLES"
		/>
	</section>
</template>

<script setup lang="ts">
import { computed, useTemplateRef } from "vue";
import { Select, TextInput, useCall, useList } from "frappe-ui";
import EmailComposer from "@/components/email/EmailComposer.vue";
import { WELCOME_VARIABLES } from "@/lib/emailVariables";
import type { EmailDocument, LeadMagnet, NewsletterTheme } from "@/types";

const leadMagnet = defineModel<string>("leadMagnet", { required: true });
const subject = defineModel<string>("subject", { required: true });
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
	return `${count} ${count === 1 ? "download" : "downloads"} so far, from all forms.`;
});

defineExpose({
	getHtml: () => composer.value?.getHtml() ?? Promise.resolve(""),
});
</script>
