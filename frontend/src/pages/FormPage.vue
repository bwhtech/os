<template>
	<PageHeader>
		<div class="min-w-0 flex-1">
			<Breadcrumbs :items="breadcrumbs" />
		</div>
		<Button
			variant="solid"
			theme="gray"
			label="Save"
			:loading="form.setValue.loading"
			:disabled="!dirty"
			@click="save"
		/>
	</PageHeader>

	<div class="mx-auto max-w-2xl space-y-8 px-3 py-6 pb-20 sm:px-5">
		<LoadingText v-if="!form.doc && !form.error" :lines="6" />
		<ErrorMessage v-else-if="form.error" :message="errorMessage(form.error)" />

		<template v-else>
			<section class="space-y-4">
				<h2 class="text-lg-semibold text-ink-gray-8">Details</h2>
				<TextInput v-model="draft.title" label="Title" required />
				<Switch
					v-model="draft.isActive"
					label="Accept signups"
					description="When off, the site shows an error instead of subscribing."
				/>
				<Switch
					v-model="draft.collectName"
					label="Collect first name"
					description="Adds a first name field to the embed snippet."
				/>
				<Switch
					v-model="draft.doubleOptIn"
					label="Double opt-in"
					description="People confirm by email before they join. Ask them to check their inbox in the success message."
				/>
			</section>

			<section class="space-y-4">
				<h2 class="text-lg-semibold text-ink-gray-8">On Signup</h2>
				<TagPicker
					v-model="draft.tags"
					description="Every subscriber from this form gets these tags."
				/>
				<Textarea
					v-model="draft.successMessage"
					label="Success message"
					description="Shown on the site after a person subscribes."
					:rows="2"
				/>
			</section>

			<ConfirmEmailSection
				v-if="draft.doubleOptIn"
				v-model:subject="draft.confirmSubject"
				v-model:body="draft.confirmBody"
			/>

			<WelcomeEmailSection
				v-model:lead-magnet="draft.leadMagnet"
				v-model:subject="draft.welcomeSubject"
				v-model:body="draft.welcomeBody"
			/>

			<EmbedSnippet :form-id="formId" :collect-name="draft.collectName" />
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, reactive, watch } from "vue";
import {
	Breadcrumbs,
	Button,
	ErrorMessage,
	LoadingText,
	PageHeader,
	Switch,
	TextInput,
	Textarea,
	toast,
	useDoc,
} from "frappe-ui";
import ConfirmEmailSection from "@/components/forms/ConfirmEmailSection.vue";
import EmbedSnippet from "@/components/forms/EmbedSnippet.vue";
import WelcomeEmailSection from "@/components/forms/WelcomeEmailSection.vue";
import TagPicker from "@/components/tags/TagPicker.vue";
import { errorMessage } from "@/lib/errors";
import type { SignupForm } from "@/types";

const props = defineProps<{ formId: string }>();

const form = useDoc<SignupForm>({
	doctype: "Signup Form",
	name: computed(() => props.formId),
});

const draft = reactive({
	title: "",
	isActive: true,
	collectName: false,
	doubleOptIn: false,
	confirmSubject: "",
	confirmBody: "",
	tags: [] as string[],
	successMessage: "",
	leadMagnet: "",
	welcomeSubject: "",
	welcomeBody: "",
});

const breadcrumbs = computed(() => [
	{ label: "Forms", route: "/forms" },
	{ label: form.doc?.title ?? props.formId },
]);

/** The saved document in draft shape, so the two compare field by field. */
const saved = computed(() => {
	const doc = form.doc;
	if (!doc) return null;
	return {
		title: doc.title,
		isActive: Boolean(doc.is_active),
		collectName: Boolean(doc.collect_name),
		doubleOptIn: Boolean(doc.double_opt_in),
		confirmSubject: doc.confirm_subject ?? "",
		confirmBody: doc.confirm_body ?? "",
		tags: doc.tags.map((row) => row.tag),
		successMessage: doc.success_message,
		leadMagnet: doc.lead_magnet ?? "",
		welcomeSubject: doc.welcome_subject ?? "",
		welcomeBody: doc.welcome_body ?? "",
	};
});

const dirty = computed(
	() => Boolean(saved.value) && JSON.stringify(saved.value) !== JSON.stringify(draft)
);

// Load the draft on first fetch and again after each save.
watch(saved, (value) => value && Object.assign(draft, structuredClone(value)), {
	immediate: true,
});

async function save() {
	try {
		await form.setValue.submit({
			title: draft.title,
			is_active: draft.isActive ? 1 : 0,
			collect_name: draft.collectName ? 1 : 0,
			double_opt_in: draft.doubleOptIn ? 1 : 0,
			confirm_subject: draft.confirmSubject,
			confirm_body: draft.confirmBody,
			success_message: draft.successMessage,
			tags: draft.tags.map((tag) => ({ tag })),
			lead_magnet: draft.leadMagnet || null,
			welcome_subject: draft.welcomeSubject,
			welcome_body: draft.welcomeBody,
		});
		toast.success("Form saved");
	} catch (error) {
		toast.error(errorMessage(error as Error));
	}
}
</script>
