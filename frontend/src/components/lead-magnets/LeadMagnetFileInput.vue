<template>
	<FileUploader @success="onUpload" @failure="onFailure">
		<template #default="{ uploading, progress, openFileSelector }">
			<div class="space-y-1.5">
				<FormLabel label="File" size="md" required />
				<div class="flex items-center gap-2 rounded-4 bg-surface-gray-2 py-1 pl-2.5 pr-1">
					<span
						class="lucide-file-text size-4 shrink-0 text-ink-gray-5"
						aria-hidden="true"
					/>
					<span
						class="min-w-0 flex-1 truncate text-base"
						:class="model ? 'text-ink-gray-8' : 'text-ink-gray-4'"
					>
						{{ model ? fileName : 'No file yet' }}
					</span>
					<Button
						size="sm"
						:label="uploading ? `Uploading ${progress}%` : model ? 'Replace' : 'Upload'"
						:loading="uploading"
						@click="openFileSelector"
					/>
				</div>
				<p class="text-p-sm text-ink-gray-5">
					Stored as a private file. People get it only through the link in their email.
				</p>
			</div>
		</template>
	</FileUploader>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button, FileUploader, FormLabel, toast } from 'frappe-ui'
import { errorMessage } from '@/lib/errors'

/** The private file URL, for example /private/files/manual.pdf. */
const model = defineModel<string>({ required: true })

const fileName = computed(() => decodeURIComponent(model.value.split('/').pop() ?? ''))

function onUpload(file: { file_url: string }) {
	model.value = file.file_url
}

function onFailure(error: unknown) {
	toast.error(error instanceof Error ? errorMessage(error) : 'Upload failed')
}
</script>
