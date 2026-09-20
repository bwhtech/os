<template>
	<AppPageHeader :breadcrumbs="breadcrumbs">
		<template #actions>
			<Button
				variant="solid"
				theme="gray"
				label="Save"
				:loading="form.setValue.loading"
				:disabled="!dirty"
				@click="save"
			/>
		</template>
	</AppPageHeader>

	<!-- A refused save keeps the page as it was, so the reason has to stay too: a toast is
	     gone in four seconds and the work goes with it on the next reload. -->
	<div v-if="saveError" class="sticky top-0 z-10 border-b border-outline-red-1 bg-surface-red-1 px-3 py-2 sm:px-5">
		<p class="text-p-sm text-ink-red-4">Not saved. {{ saveError }}</p>
	</div>

	<!-- Wide enough for the email editor and its inspector. Form fields keep a narrow column. -->
	<div class="mx-auto max-w-5xl space-y-8 px-3 py-6 pb-20 sm:px-5">
		<DetailSkeleton v-if="!form.doc && !form.error" />
		<ErrorMessage v-else-if="form.error" :message="errorMessage(form.error)" />

		<template v-else>
			<ActivityCards
				method="bwh_os.mailing.api.get_form_activity"
				:params="{ form_id: formId }"
				label="Signups"
			>
				<ConfirmRateCard v-if="form.doc?.double_opt_in" :form-id="formId" />
			</ActivityCards>

			<section class="max-w-2xl space-y-4">
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

			<section class="max-w-2xl space-y-4">
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
				<LeadMagnetPicker
					v-model="draft.leadMagnet"
					description="Gives the file away on signup, through its own delivery email."
				/>
				<Switch
					v-if="draft.leadMagnet"
					v-model="draft.sendWelcomeWithLeadMagnet"
					label="Also send the welcome email"
					description="They get your greeting first, then the file."
				/>
			</section>

			<ConfirmEmailSection
				v-if="draft.doubleOptIn"
				ref="confirmEmail"
				v-model:subject="draft.confirmSubject"
				v-model:reply-to="draft.confirmReplyTo"
				v-model:content="draft.confirmContent"
				v-model:theme="draft.confirmTheme"
			/>

			<!-- The editor reads its content once, so it mounts only after the first fetch. -->
			<WelcomeEmailSection
				v-if="loaded"
				ref="welcomeEmail"
				v-model:subject="draft.welcomeSubject"
				v-model:reply-to="draft.welcomeReplyTo"
				v-model:content="draft.welcomeContent"
				v-model:theme="draft.welcomeTheme"
			/>

			<EmbedSnippet class="max-w-2xl" :form-id="formId" :collect-name="draft.collectName" />
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, useTemplateRef, watch } from "vue";
import {
	Button,
	ErrorMessage,
	Switch,
	TextInput,
	Textarea,
	toast,
	useDoc,
} from "frappe-ui";
import AppPageHeader from "@/components/shell/AppPageHeader.vue";
import DetailSkeleton from "@/components/stats/DetailSkeleton.vue";
import ConfirmEmailSection from "@/components/forms/ConfirmEmailSection.vue";
import ConfirmRateCard from "@/components/forms/ConfirmRateCard.vue";
import EmbedSnippet from "@/components/forms/EmbedSnippet.vue";
import ActivityCards from "@/components/stats/ActivityCards.vue";
import WelcomeEmailSection from "@/components/forms/WelcomeEmailSection.vue";
import LeadMagnetPicker from "@/components/lead-magnets/LeadMagnetPicker.vue";
import TagPicker from "@/components/tags/TagPicker.vue";
import { confirmStarter, parseEmailDocument, welcomeStarter } from "@/lib/emailStarters";
import { useSaveShortcut } from "@/composables/useSaveShortcut";
import { useUnsavedChanges } from "@/composables/useUnsavedChanges";
import { errorMessage } from "@/lib/errors";
import type { EmailDocument, NewsletterTheme, SignupForm } from "@/types";

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
	confirmReplyTo: "",
	confirmContent: null as EmailDocument | null,
	confirmTheme: "Frappe UI" as NewsletterTheme,
	tags: [] as string[],
	successMessage: "",
	leadMagnet: "",
	sendWelcomeWithLeadMagnet: true,
	welcomeSubject: "",
	welcomeReplyTo: "",
	welcomeContent: null as EmailDocument | null,
	welcomeTheme: "Frappe UI" as NewsletterTheme,
});

const saveError = ref("");

const confirmEmail = useTemplateRef<InstanceType<typeof ConfirmEmailSection>>("confirmEmail");
const welcomeEmail = useTemplateRef<InstanceType<typeof WelcomeEmailSection>>("welcomeEmail");
const loaded = ref(false);
/** The form the draft was read from. See the watcher below. */
const loadedName = ref("");

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
		confirmReplyTo: doc.confirm_reply_to ?? "",
		// A form with no email yet starts from a first draft.
		confirmContent: parseEmailDocument(doc.confirm_content_json) ?? confirmStarter(),
		confirmTheme: doc.confirm_theme,
		tags: doc.tags.map((row) => row.tag),
		successMessage: doc.success_message,
		leadMagnet: doc.lead_magnet ?? "",
		sendWelcomeWithLeadMagnet: Boolean(doc.send_welcome_with_lead_magnet ?? 1),
		welcomeSubject: doc.welcome_subject ?? "",
		welcomeReplyTo: doc.welcome_reply_to ?? "",
		welcomeContent: parseEmailDocument(doc.welcome_content_json) ?? welcomeStarter(),
		welcomeTheme: doc.welcome_theme,
	};
});

const dirty = computed(
	() => Boolean(saved.value) && JSON.stringify(saved.value) !== JSON.stringify(draft)
);

// Everything on this page is written by hand and saved by a button, so a reload is how an
// afternoon disappears.
useUnsavedChanges(dirty, "This form has changes that are not saved. Leave anyway?");

/**
 * Load the draft once per form. The document comes back from the server on its own — after
 * a save, on a socket update, when the tab wakes — and reading it again would throw away
 * whatever is being written. Keying on the name means another form still loads.
 */
watch(
	saved,
	(value) => {
		const name = form.doc?.name;
		if (!value || !name || name === loadedName.value) return;
		loadedName.value = name;
		Object.assign(draft, structuredClone(value));
		loaded.value = true;
	},
	{ immediate: true }
);

async function save() {
	try {
		await form.setValue.submit({
			title: draft.title,
			is_active: draft.isActive ? 1 : 0,
			collect_name: draft.collectName ? 1 : 0,
			double_opt_in: draft.doubleOptIn ? 1 : 0,
			confirm_subject: draft.confirmSubject,
			confirm_reply_to: draft.confirmReplyTo || null,
			confirm_theme: draft.confirmTheme,
			confirm_content_json: JSON.stringify(draft.confirmContent),
			// A hidden confirm editor keeps the saved email.
			confirm_content_html: confirmEmail.value
				? await confirmEmail.value.getHtml()
				: form.doc?.confirm_content_html,
			success_message: draft.successMessage,
			tags: draft.tags.map((tag) => ({ tag })),
			lead_magnet: draft.leadMagnet || null,
			send_welcome_with_lead_magnet: draft.sendWelcomeWithLeadMagnet ? 1 : 0,
			welcome_subject: draft.welcomeSubject,
			welcome_reply_to: draft.welcomeReplyTo || null,
			welcome_theme: draft.welcomeTheme,
			welcome_content_json: JSON.stringify(draft.welcomeContent),
			welcome_content_html: (await welcomeEmail.value?.getHtml()) ?? form.doc?.welcome_content_html,
		});
		saveError.value = "";
		toast.success("Form saved");
	} catch (error) {
		saveError.value = errorMessage(error as Error);
		toast.error(saveError.value);
	}
}

// Cmd+S is muscle memory for anyone writing an email, and the button is at the top of a
// long page.
useSaveShortcut(() => {
	if (dirty.value && !form.setValue.loading) save();
});
</script>
