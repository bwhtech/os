<template>
	<AppPageHeader title="Posts" />

	<div class="flex flex-col items-center justify-center gap-3 px-3 py-16 text-center sm:px-5">
		<div class="rounded-full bg-surface-gray-2 p-3 text-ink-gray-5">
			<span class="lucide-megaphone size-6" aria-hidden="true" />
		</div>
		<p class="text-base text-ink-gray-7">No posts yet</p>
		<p class="max-w-sm text-sm text-ink-gray-5">
			Connect LinkedIn or X in Settings, then write a post here and pick when it goes out.
		</p>
	</div>
</template>

<script setup lang="ts">
import AppPageHeader from '@/components/shell/AppPageHeader.vue'

/** Social posts. The list, the composer, and the calendar land here. See specs/04-social-posts.md. */
</script>
