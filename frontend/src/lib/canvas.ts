import { call } from 'frappe-ui'

/** The Excalidraw shape library. Every canvas shares one. */
export function loadCanvasLibrary() {
	return call<string | null>('bwh_os.canvas.api.get_library')
}

export async function saveCanvasLibrary(items: string) {
	await call('bwh_os.canvas.api.save_library', { items })
}
