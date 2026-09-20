<template>
	<!-- `class` falls through to this single root element on its own. -->
	<Select
		v-model="leadMagnet"
		:label="label"
		:description="description"
		placeholder="None"
		:options="options"
	/>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { Select, useList } from "frappe-ui";
import type { LeadMagnet } from "@/types";

withDefaults(
	defineProps<{
		label?: string
		description?: string
	}>(),
	{ label: "Lead magnet", description: undefined },
);

const leadMagnet = defineModel<string>({ required: true });

const leadMagnets = useList<LeadMagnet>({
	doctype: "Lead Magnet",
	fields: ["name", "title"],
	orderBy: "title asc",
	limit: 200,
});

const options = computed(() => [
	{ label: "None", value: "" },
	...(leadMagnets.data ?? []).map((item) => ({ label: item.title, value: item.name })),
]);
</script>
