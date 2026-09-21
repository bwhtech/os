import { createRoot } from 'react-dom/client'
import { Excalidraw, hashElementsVersion, serializeAsJSON } from '@excalidraw/excalidraw'
import type { ExcalidrawElement } from '@excalidraw/excalidraw/element/types'
import type { AppState, BinaryFiles, ExcalidrawInitialDataState } from '@excalidraw/excalidraw/types'
import '@excalidraw/excalidraw/index.css'
import type { CanvasMountOptions, CanvasTheme, MountedCanvas } from './api'

/** Mount Excalidraw in `host`. It fills the host, so the host needs a height. */
export function mountCanvas(host: HTMLElement, options: CanvasMountOptions): MountedCanvas {
	const root = createRoot(host)
	const initialData = parseScene(options.scene)
	let lastKey: string | null = null

	// Excalidraw calls onChange for every pointer move, scroll and selection. Only a change
	// to the drawing itself is worth a save. The first call is the scene it loaded.
	function onChange(elements: readonly ExcalidrawElement[], appState: AppState, files: BinaryFiles) {
		const key = changeKey(elements, appState)
		const loaded = lastKey === null
		if (key === lastKey) return
		lastKey = key
		if (loaded) return
		// "local" keeps pasted images in the scene, as data URLs.
		options.onChange(serializeAsJSON(elements, appState, files, 'local'))
	}

	const render = (theme: CanvasTheme) =>
		root.render(<Excalidraw initialData={initialData} theme={theme} onChange={onChange} />)

	render(options.theme)
	return { setTheme: render, unmount: () => root.unmount() }
}

function parseScene(scene: string | null): ExcalidrawInitialDataState | null {
	if (!scene) return null
	try {
		return JSON.parse(scene)
	} catch {
		return null
	}
}

/** Changes when an element or the background changes, and not when the view moves. */
function changeKey(elements: readonly ExcalidrawElement[], appState: AppState) {
	return `${hashElementsVersion(elements)}:${appState.viewBackgroundColor ?? ''}`
}
