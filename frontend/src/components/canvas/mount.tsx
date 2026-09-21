import { createRoot } from 'react-dom/client'
import { Excalidraw, hashElementsVersion, restoreElements, serializeAsJSON } from '@excalidraw/excalidraw'
import type { ExcalidrawElement } from '@excalidraw/excalidraw/element/types'
import type {
	AppState,
	BinaryFiles,
	ExcalidrawImperativeAPI,
	ExcalidrawInitialDataState,
} from '@excalidraw/excalidraw/types'
import '@excalidraw/excalidraw/index.css'
import type { CanvasMountOptions, CanvasTheme, MountedCanvas } from './api'

/** How long a stroke pauses before the scene is reported. Other windows update this often. */
const REPORT_DELAY = 250

/** Mount Excalidraw in `host`. It fills the host, so the host needs a height. */
export function mountCanvas(host: HTMLElement, options: CanvasMountOptions): MountedCanvas {
	const root = createRoot(host)
	const initialData = parseScene(options.scene)
	let api: ExcalidrawImperativeAPI | null = null
	let lastKey: string | null = null
	let pending: (() => string) | null = null
	let timer: ReturnType<typeof setTimeout> | undefined

	// Excalidraw calls onChange for every pointer move, scroll and selection. Only a change
	// to the drawing itself is worth a save. The first call is the scene it loaded.
	function onChange(elements: readonly ExcalidrawElement[], appState: AppState, files: BinaryFiles) {
		const key = changeKey(elements, appState.viewBackgroundColor)
		const loaded = lastKey === null
		if (key === lastKey) return
		lastKey = key
		if (loaded) return
		// A stroke changes the scene on every pointer move, and the whole scene is turned into
		// JSON for each report, so report once the stroke pauses. "local" keeps pasted images
		// in the scene, as data URLs.
		pending = () => serializeAsJSON(elements, appState, files, 'local')
		clearTimeout(timer)
		timer = setTimeout(report, REPORT_DELAY)
	}

	function report() {
		clearTimeout(timer)
		if (pending) options.onChange(pending())
		pending = null
	}

	/** Show a scene drawn somewhere else. It is already saved, so it does not count as a change. */
	function setScene(scene: string) {
		const data = parseScene(scene)
		if (!api || !data) return
		const elements = restoreElements(data.elements, api.getSceneElementsIncludingDeleted())
		const background = data.appState?.viewBackgroundColor ?? api.getAppState().viewBackgroundColor
		lastKey = changeKey(elements, background)
		if (data.files) api.addFiles(Object.values(data.files))
		api.updateScene({ elements, appState: { viewBackgroundColor: background } })
	}

	const render = (theme: CanvasTheme) =>
		root.render(
			<Excalidraw
				initialData={initialData}
				theme={theme}
				onChange={onChange}
				excalidrawAPI={(value) => (api = value)}
			/>,
		)

	render(options.theme)
	return {
		setTheme: render,
		setScene,
		unmount: () => {
			// The last stroke is not lost when the page closes the canvas.
			report()
			root.unmount()
		},
	}
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
function changeKey(elements: readonly ExcalidrawElement[], background: string | undefined) {
	return `${hashElementsVersion(elements)}:${background ?? ''}`
}
