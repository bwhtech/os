<template>
	<div v-if="!canvas.doc" class="px-3 py-6 sm:px-5">
		<ErrorMessage v-if="canvas.error" :message="errorMessage(canvas.error)" />
		<DetailSkeleton v-else class="mx-auto max-w-[770px]" />
	</div>

	<!-- A new key for each canvas, because the editor reads the scene only when it mounts. -->
	<CanvasEditor v-else :key="canvas.doc.name" :scene="canvas.doc.scene" @change="(scene) => queue({ scene })" />
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { ErrorMessage, useDoc } from 'frappe-ui'
import CanvasEditor from '@/components/canvas/CanvasEditor.vue'
import DetailSkeleton from '@/components/stats/DetailSkeleton.vue'
import { type SaveState, useAutosave } from '@/composables/useAutosave'
import { errorMessage } from '@/lib/errors'
import type { Canvas } from '@/types'

/** A saved canvas: loads it, draws it, and saves it as it changes. */
const props = defineProps<{ canvasId: string }>()

/** For the page to show next to its header. */
const saveState = defineModel<SaveState>('saveState', { default: 'idle' })

const canvas = useDoc<Canvas>({ doctype: 'BWH Canvas', name: computed(() => props.canvasId) })

// A drawing changes many times a second, so wait for a longer pause than the text editors do.
const { state, queue, flush } = useAutosave<Canvas>((values) => canvas.setValue.submit(values), 1500)

watch(state, (value) => (saveState.value = value), { immediate: true })

defineExpose({ flush })
</script>
