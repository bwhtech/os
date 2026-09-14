import type { JSONContent } from '@tiptap/core'
import type { NewsletterTheme } from '@/types'
import type { EmailVariable } from '@/lib/emailVariables'

/**
 * What the Vue app sees of the React Email editor. The app imports this file, never
 * `mount.tsx`: React Email and frappe-ui/editor declare the same Tiptap commands with
 * different types, so the two editors typecheck as separate projects. See tsconfig.email.json.
 */

export interface EmailEditorApi {
	/** Email-safe HTML for the current document, as a full HTML document. */
	getHtml: (previewText: string) => Promise<string>
}

export interface MountOptions {
	content: JSONContent | null
	theme: NewsletterTheme
	/** The `{{` menu offers these. With none, the editor has no variables. */
	variables: EmailVariable[]
	onChange: (json: JSONContent) => void
	onReady: (api: EmailEditorApi) => void
	uploadImage: (file: File) => Promise<{ url: string }>
}

export interface MountedEmailEditor {
	/** Restyle the current content. The undo history starts again. */
	setTheme: (theme: NewsletterTheme) => void
	unmount: () => void
}

/** Mount the React Email editor in a shadow root. Implemented in `mount.tsx`. */
export declare function mountEmailEditor(shadow: ShadowRoot, options: MountOptions): MountedEmailEditor
