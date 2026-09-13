<template>
	<section class="space-y-4">
		<div class="space-y-1">
			<h2 class="text-lg-semibold text-ink-gray-8">Confirm Email</h2>
			<p class="text-p-sm text-ink-gray-5">
				Sent when a person signs up. The person stays Pending, and gets the welcome email
				only after they confirm.
			</p>
		</div>

		<TextInput v-model="subject" label="Subject" required />
		<EmailBodyEditor
			v-model="body"
			placeholder="Ask the person to confirm…"
			hint="The confirm button goes below the body."
		/>
	</section>
</template>

<script setup lang="ts">
import { TextInput } from "frappe-ui";
import EmailBodyEditor from "@/components/forms/EmailBodyEditor.vue";

const subject = defineModel<string>("subject", { required: true });
const body = defineModel<string>("body", { required: true });
</script>
