<template>
	<Dialog :open="open" title="Web Archive" @update:open="emit('update:open', $event)">
		<template #default="{ close }">
			<form class="space-y-4" @submit.prevent="submit(close)">
				<Switch
					v-model="isPublic"
					label="Show in web archive"
					description="Anyone can read it at /newsletter. The page has no tracking and no unsubscribe link."
				/>
				<TextInput
					v-if="isPublic"
					v-model="route"
					label="Route"
					:placeholder="issue.subject"
					:description="`/newsletter/${route || 'made-from-the-subject'}`"
				/>

				<ErrorMessage :message="error" />

				<div class="flex items-center justify-between gap-2 pt-2">
					<Button
						v-if="pageUrl"
						variant="ghost"
						icon-left="lucide-external-link"
						label="Open Page"
						:link="pageUrl"
					/>
					<div class="ml-auto flex gap-2">
						<Button label="Cancel" @click="close" />
						<Button type="submit" variant="solid" theme="gray" label="Save" :loading="saving" />
					</div>
				</div>
			</form>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Button, Dialog, ErrorMessage, Switch, TextInput, toast } from 'frappe-ui'
import { errorMessage } from '@/lib/errors'
import type { NewsletterIssue } from '@/types'

const props = defineProps<{
	open: boolean
	issue: NewsletterIssue
	/** Saves the fields and resolves when the doc is fresh */
	save: (values: Pick<NewsletterIssue, 'is_public' | 'route'>) => Promise<unknown>
}>()
const emit = defineEmits<{ 'update:open': [open: boolean] }>()

const isPublic = ref(false)
const route = ref('')
const saving = ref(false)
const error = ref('')

/** The saved page, not the one being typed */
const pageUrl = computed(() =>
	props.issue.is_public && props.issue.route
		? `${window.location.origin}/newsletter/${props.issue.route}`
		: null,
)

watch(
	() => props.open,
	(open) => {
		if (!open) return
		isPublic.value = Boolean(props.issue.is_public)
		route.value = props.issue.route ?? ''
		error.value = ''
	},
)

async function submit(close: () => void) {
	saving.value = true
	error.value = ''
	try {
		// The server makes the route a unique slug.
		await props.save({ is_public: isPublic.value ? 1 : 0, route: route.value || null })
		toast.success(isPublic.value ? 'Newsletter is in the web archive' : 'Newsletter is private')
		close()
	} catch (e) {
		error.value = errorMessage(e as Error)
	} finally {
		saving.value = false
	}
}
</script>
