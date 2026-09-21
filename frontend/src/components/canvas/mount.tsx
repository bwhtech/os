import { useState } from 'react'
import { createRoot } from 'react-dom/client'
import {
	Excalidraw,
	exportToBlob,
	hashElementsVersion,
	restoreElements,
	serializeAsJSON,
	useHandleLibrary,
} from '@excalidraw/excalidraw'
import type { LibraryPersistenceAdapter } from '@excalidraw/excalidraw/data/library'
import type { ExcalidrawElement, FileId } from '@excalidraw/excalidraw/element/types'
import type {
	AppState,
	BinaryFileData,
	BinaryFiles,
	DataURL,
	ExcalidrawImperativeAPI,
	ExcalidrawInitialDataState,
} from '@excalidraw/excalidraw/types'
import '@excalidraw/excalidraw/index.css'
import type { CanvasMountOptions, CanvasTheme, MountedCanvas } from './api'

/** How long a stroke pauses before the scene is reported. Other windows update this often. */
const REPORT_DELAY = 250

/** Drawing the thumbnail renders the whole scene, so it waits for a longer pause. */
const THUMBNAIL_DELAY = 3000

/**
 * A pasted image as the scene keeps it: the uploaded file's URL, not its data. Scenes saved
 * before uploads existed hold `dataURL` instead, and upload it on their next change.
 */
interface StoredFile {
	id: FileId
	mimeType: BinaryFileData['mimeType']
	created: number
	url?: string
	dataURL?: DataURL
}

interface StoredScene extends Omit<ExcalidrawInitialDataState, 'files'> {
	files?: Record<string, StoredFile>
}

interface Snapshot {
	elements: readonly ExcalidrawElement[]
	appState: AppState
	files: BinaryFiles
}

/** Mount Excalidraw in `host`. It fills the host, so the host needs a height. */
export function mountCanvas(host: HTMLElement, options: CanvasMountOptions): MountedCanvas {
	const root = createRoot(host)
	const initialScene = parseScene(options.scene)
	const uploads = new Uploads(options.uploadFile, () => latest && report())
	let api: ExcalidrawImperativeAPI | null = null
	let lastKey: string | null = null
	let latest: Snapshot | null = null
	let reportTimer: ReturnType<typeof setTimeout> | undefined
	let thumbnailTimer: ReturnType<typeof setTimeout> | undefined
	let thumbnailDue = false

	// Excalidraw calls onChange for every pointer move, scroll and selection. Only a change
	// to the drawing itself is worth a save. The first call is the scene it loaded.
	function onChange(elements: readonly ExcalidrawElement[], appState: AppState, files: BinaryFiles) {
		const key = changeKey(elements, appState.viewBackgroundColor)
		const loaded = lastKey === null
		if (key === lastKey) return
		lastKey = key
		if (loaded) return
		// A stroke changes the scene on every pointer move, and the whole scene is turned into
		// JSON for each report, so report once the stroke pauses.
		latest = { elements, appState, files }
		clearTimeout(reportTimer)
		reportTimer = setTimeout(report, REPORT_DELAY)
		thumbnailDue = true
		clearTimeout(thumbnailTimer)
		thumbnailTimer = setTimeout(thumbnail, THUMBNAIL_DELAY)
	}

	function report() {
		clearTimeout(reportTimer)
		reportTimer = undefined
		if (!latest) return
		const { elements, appState, files } = latest
		// An image waits for its upload. Its element is saved now, and its file once uploaded.
		uploads.start(usedFiles(elements, files))
		options.onChange(serializeAsJSON(elements, appState, uploads.stored(elements, files), 'local'))
	}

	async function thumbnail() {
		clearTimeout(thumbnailTimer)
		thumbnailDue = false
		if (!latest) return
		const { appState, files } = latest
		const elements = latest.elements.filter((element) => !element.isDeleted)
		if (!elements.length) return options.onThumbnail(null)
		const blob = await exportToBlob({
			elements,
			files,
			appState: { ...appState, exportBackground: true, exportWithDarkMode: false },
			mimeType: 'image/jpeg',
			quality: 0.8,
			maxWidthOrHeight: 480,
		})
		options.onThumbnail(await toDataURL(blob))
	}

	/** Show a scene drawn somewhere else. It is already saved, so it does not count as a change. */
	function setScene(scene: string) {
		const data = parseScene(scene)
		if (!api || !data) return
		const elements = restoreElements(data.elements, api.getSceneElementsIncludingDeleted())
		const background = data.appState?.viewBackgroundColor ?? api.getAppState().viewBackgroundColor
		lastKey = changeKey(elements, background)
		api.updateScene({ elements, appState: { viewBackgroundColor: background } })
		void addFiles(api, uploads, data.files)
	}

	function onApi(value: ExcalidrawImperativeAPI) {
		if (api) return
		api = value
		void addFiles(api, uploads, initialScene?.files)
	}

	const library = libraryAdapter(options)
	const initialData = initialScene ? { ...initialScene, files: undefined } : null
	const render = (theme: CanvasTheme) =>
		root.render(
			<Canvas initialData={initialData} theme={theme} library={library} onChange={onChange} onApi={onApi} />,
		)

	render(options.theme)
	return {
		setTheme: render,
		setScene,
		unmount: () => {
			// The last stroke is not lost when the page closes the canvas.
			if (reportTimer) report()
			if (thumbnailDue) void thumbnail()
			root.unmount()
		},
	}
}

function Canvas(props: {
	initialData: ExcalidrawInitialDataState | null
	theme: CanvasTheme
	library: LibraryPersistenceAdapter
	onChange: (elements: readonly ExcalidrawElement[], appState: AppState, files: BinaryFiles) => void
	onApi: (api: ExcalidrawImperativeAPI) => void
}) {
	const [api, setApi] = useState<ExcalidrawImperativeAPI | null>(null)
	// Loads the saved library, saves it on change, and installs one picked on libraries.excalidraw.com.
	useHandleLibrary({ excalidrawAPI: api, adapter: props.library })
	return (
		<Excalidraw
			initialData={props.initialData}
			theme={props.theme}
			onChange={props.onChange}
			excalidrawAPI={(value) => {
				setApi(value)
				props.onApi(value)
			}}
		/>
	)
}

/** Pasted images go up as private files attached to the canvas, once each. */
class Uploads {
	private urls = new Map<string, string>()
	private pending = new Set<string>()

	constructor(
		private upload: CanvasMountOptions['uploadFile'],
		private onUploaded: () => void,
	) {}

	remember(id: string, url: string) {
		this.urls.set(id, url)
	}

	start(files: BinaryFileData[]) {
		for (const file of files) {
			if (this.urls.has(file.id) || this.pending.has(file.id)) continue
			this.pending.add(file.id)
			this.upload(toFile(file))
				.then((url) => {
					this.urls.set(file.id, url)
					this.onUploaded()
				})
				.catch(() => {
					// Left out of the scene. The next change tries again.
				})
				.finally(() => this.pending.delete(file.id))
		}
	}

	/** The files to save with the scene: the uploaded ones, by URL. */
	stored(elements: readonly ExcalidrawElement[], files: BinaryFiles): BinaryFiles {
		const stored: Record<string, StoredFile> = {}
		for (const file of usedFiles(elements, files)) {
			const url = this.urls.get(file.id)
			if (url) stored[file.id] = { id: file.id, mimeType: file.mimeType, created: file.created, url }
		}
		// serializeAsJSON passes the files through as they are.
		return stored as unknown as BinaryFiles
	}
}

/** Give Excalidraw the image data of the files it does not have yet. */
async function addFiles(api: ExcalidrawImperativeAPI, uploads: Uploads, files: StoredScene['files']) {
	const stored = Object.values(files ?? {})
	for (const file of stored) if (file.url) uploads.remember(file.id, file.url)
	const have = api.getFiles()
	const loaded = await Promise.all(
		stored
			.filter((file) => !have[file.id])
			.map(async (file) => {
				const dataURL = file.dataURL ?? (file.url ? await fetchDataURL(file.url) : null)
				return dataURL ? { id: file.id, mimeType: file.mimeType, created: file.created, dataURL } : null
			}),
	)
	api.addFiles(loaded.filter((file) => file !== null))
}

function libraryAdapter(options: CanvasMountOptions): LibraryPersistenceAdapter {
	return {
		async load() {
			const items = await options.loadLibrary()
			return items ? { libraryItems: JSON.parse(items) } : null
		},
		async save({ libraryItems }) {
			await options.saveLibrary(JSON.stringify(libraryItems))
		},
	}
}

function usedFiles(elements: readonly ExcalidrawElement[], files: BinaryFiles): BinaryFileData[] {
	const used: BinaryFileData[] = []
	for (const element of elements) {
		if (element.isDeleted || element.type !== 'image' || !element.fileId) continue
		const file = files[element.fileId]
		if (file) used.push(file)
	}
	return used
}

function parseScene(scene: string | null): StoredScene | null {
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

function toFile(file: BinaryFileData): File {
	const [header, data] = file.dataURL.split(',')
	const bytes = Uint8Array.from(atob(data), (char) => char.charCodeAt(0))
	const extension = file.mimeType.split('/')[1]?.replace('svg+xml', 'svg') ?? 'bin'
	return new File([bytes], `canvas-${file.id.slice(0, 12)}.${extension}`, {
		type: header.slice(5).split(';')[0],
	})
}

async function fetchDataURL(url: string): Promise<DataURL | null> {
	try {
		const response = await fetch(url)
		return response.ok ? await toDataURL(await response.blob()) : null
	} catch {
		return null
	}
}

function toDataURL(blob: Blob): Promise<DataURL> {
	return new Promise((resolve, reject) => {
		const reader = new FileReader()
		reader.onload = () => resolve(reader.result as DataURL)
		reader.onerror = () => reject(reader.error)
		reader.readAsDataURL(blob)
	})
}
