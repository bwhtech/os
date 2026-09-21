<template>
	<!-- The whole window is the canvas, for screen recorders that capture one window. -->
	<CanvasDocEditor :key="canvasId" class="h-dvh" :canvas-id="canvasId" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useDoc, usePageMeta } from 'frappe-ui'
import CanvasDocEditor from '@/components/canvas/CanvasDocEditor.vue'
import type { Canvas } from '@/types'

const props = defineProps<{ canvasId: string }>()

// The same document as the editor's. The title names the window in a recorder's window list.
const canvas = useDoc<Canvas>({ doctype: 'BWH Canvas', name: computed(() => props.canvasId) })

usePageMeta(() => ({ title: canvas.doc?.title || 'Canvas' }))
</script>
