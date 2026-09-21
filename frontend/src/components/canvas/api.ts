/**
 * What the Vue app sees of the Excalidraw canvas. `mount.tsx` implements it. The page
 * imports `mount.tsx` lazily, because React and Excalidraw are large.
 */

export type CanvasTheme = 'light' | 'dark'

export interface CanvasMountOptions {
	/** The saved scene, as `serializeAsJSON` wrote it. Null for a new canvas. */
	scene: string | null
	theme: CanvasTheme
	/** Called with the serialized scene after a change to the drawing. Not for scroll, zoom or selection. */
	onChange: (scene: string) => void
	/** Called with a small JPEG of the drawing, as a data URL, a while after it changes. Null when empty. */
	onThumbnail: (thumbnail: string | null) => void
	/** Store a pasted image and give back its URL. The scene keeps the URL, not the image. */
	uploadFile: (file: File) => Promise<string>
	/** The shared shape library, as JSON. */
	loadLibrary: () => Promise<string | null>
	saveLibrary: (items: string) => Promise<void>
}

export interface MountedCanvas {
	setTheme: (theme: CanvasTheme) => void
	/** Replace the drawing with a scene saved somewhere else, such as another window. */
	setScene: (scene: string) => void
	unmount: () => void
}
