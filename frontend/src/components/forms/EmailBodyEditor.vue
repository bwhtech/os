<template>
	<div class="space-y-1.5">
		<FormLabel label="Body" size="md" />
		<Editor v-model="body" :extensions="extensions" :placeholder="placeholder">
			<template #default="{ editor }">
				<div
					class="rounded-4 border border-outline-gray-2 bg-surface-base focus-within:border-outline-gray-4"
				>
					<EditorContent :editor="editor" class="min-h-32 px-3 py-2" />
					<div class="border-t border-outline-gray-2 px-2 py-1.5">
						<EditorFixedMenu
							:editor="editor"
							:items="minimalToolbar"
							button-size="xs"
						/>
					</div>
				</div>
			</template>
		</Editor>
		<p class="text-p-sm text-ink-gray-5">
			Use <code v-pre class="font-mono">{{ first_name or "there" }}</code> for the first
			name, since not every form asks for it. {{ hint }}
		</p>
	</div>
</template>

<script setup lang="ts">
import { FormLabel } from "frappe-ui";
import {
	CommentKit,
	Editor,
	EditorContent,
	EditorFixedMenu,
	minimalToolbar,
} from "frappe-ui/editor";

defineProps<{ placeholder: string; hint: string }>();

const body = defineModel<string>({ required: true });

// Email clients need public image URLs, so the body has no uploads.
const extensions = [CommentKit.configure({ image: false })];
</script>
