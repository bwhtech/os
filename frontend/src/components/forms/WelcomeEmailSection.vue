<template>
	<section class="space-y-4">
		<div class="space-y-1">
			<h2 class="text-lg-semibold text-ink-gray-8">Welcome Email</h2>
			<p class="text-p-sm text-ink-gray-5">
				Sent once, when a new person signs up. Leave the subject empty to send nothing.
			</p>
		</div>

		<Select
			v-model="leadMagnet"
			label="Lead magnet"
			:description="leadMagnetDescription"
			placeholder="None"
			:options="leadMagnetOptions"
		/>
		<TextInput
			v-model="subject"
			label="Subject"
			placeholder="Here is your manual, {{ first_name }}"
			:required="Boolean(leadMagnet)"
		/>

		<EmailBodyEditor
			v-model="body"
			placeholder="Write the welcome email…"
			hint="The download button goes below the body."
		/>
	</section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { Select, TextInput, useCall, useList } from "frappe-ui";
import EmailBodyEditor from "@/components/forms/EmailBodyEditor.vue";
import type { LeadMagnet } from "@/types";

const leadMagnet = defineModel<string>("leadMagnet", { required: true });
const subject = defineModel<string>("subject", { required: true });
const body = defineModel<string>("body", { required: true });

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
</script>
