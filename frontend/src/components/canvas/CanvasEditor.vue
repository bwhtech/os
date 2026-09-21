<template>
	<div class="relative">
		<div ref="host" class="absolute inset-0" />
		<div v-if="!ready" class="absolute inset-0 grid place-items-center">
			<LoadingIndicator class="size-5 text-ink-gray-5" />
		</div>
	</div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { LoadingIndicator, useColorScheme } from 'frappe-ui'
import type { MountedCanvas } from '@/components/canvas/api'

/** The scene is read once, at mount. The canvas keeps its own state after that. */
const props = defineProps<{ scene: string | null }>()
const emit = defineEmits<{ change: [scene: string] }>()

const { resolvedColorScheme } = useColorScheme()

const host = ref<HTMLElement>()
const ready = ref(false)
let mounted: MountedCanvas | null = null

onMounted(async () => {
	// React and Excalidraw are large, so they load only when a canvas opens.
	const { mountCanvas } = await import('@/components/canvas/mount')
	if (!host.value) return
	mounted = mountCanvas(host.value, {
		scene: props.scene,
		theme: resolvedColorScheme.value,
		onChange: (scene) => emit('change', scene),
	})
	ready.value = true
})

watch(resolvedColorScheme, (theme) => mounted?.setTheme(theme))

onBeforeUnmount(() => mounted?.unmount())

defineExpose({
	/** Replace the drawing with a scene saved somewhere else. It does not emit `change`. */
	setScene: (scene: string) => mounted?.setScene(scene),
})
</script>
