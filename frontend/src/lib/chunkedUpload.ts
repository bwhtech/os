/**
 * Uploading a big file to Frappe in pieces. See specs/04-social-posts.md.
 *
 * `upload_file` takes a file in chunks: each request carries one slice and where it
 * belongs, the server appends it to a temporary file, and the last one comes back as the
 * `File`. Chunks keep a 200 MB video off the request size limit of the proxy in front of
 * the site, and they are what makes a progress bar honest.
 */

/** 5 MB: big enough that a 200 MB video is 40 requests, small enough to pass any proxy. */
const CHUNK_SIZE = 5 * 1024 * 1024

export interface UploadedFile {
	name: string
	file_url: string
	file_name: string
	file_size: number
}

export interface ChunkedUploadOptions {
	/** The document the file attaches to, so it has an owner from the start */
	doctype?: string
	docname?: string
	/** Whole fraction of the file that has arrived, from 0 to 1 */
	onProgress?: (done: number) => void
	signal?: AbortSignal
}

export async function chunkedUpload(file: File, options: ChunkedUploadOptions = {}): Promise<UploadedFile> {
	const total = Math.max(1, Math.ceil(file.size / CHUNK_SIZE))
	let uploaded: UploadedFile | null = null

	for (let index = 0; index < total; index++) {
		const offset = index * CHUNK_SIZE
		const slice = file.slice(offset, offset + CHUNK_SIZE)
		const answer = await send(slice, file, { index, total, offset }, options)
		// Only the last chunk answers with the document; the others answer with nothing.
		if (answer) uploaded = answer
	}

	if (!uploaded) throw new Error('The upload finished without a file')
	return uploaded
}

interface ChunkPosition {
	index: number
	total: number
	offset: number
}

function send(
	slice: Blob,
	file: File,
	at: ChunkPosition,
	options: ChunkedUploadOptions,
): Promise<UploadedFile | null> {
	const form = new FormData()
	form.append('file', slice, file.name)
	form.append('file_name', file.name)
	form.append('is_private', '1')
	form.append('folder', 'Home')
	form.append('chunk_index', String(at.index))
	form.append('total_chunk_count', String(at.total))
	form.append('chunk_byte_offset', String(at.offset))
	form.append('total_file_size', String(file.size))
	if (options.doctype) form.append('doctype', options.doctype)
	if (options.docname) form.append('docname', options.docname)

	return new Promise((resolve, reject) => {
		const request = new XMLHttpRequest()
		request.open('POST', '/api/method/upload_file', true)
		request.setRequestHeader('Accept', 'application/json')
		const token = window.csrf_token
		if (token && token !== '{{ csrf_token }}') request.setRequestHeader('X-Frappe-CSRF-Token', token)

		// Progress covers the whole file, not this chunk: the bar belongs to what was picked.
		request.upload.addEventListener('progress', (event) => {
			if (!event.lengthComputable || !options.onProgress) return
			options.onProgress(Math.min(1, (at.offset + event.loaded) / Math.max(file.size, 1)))
		})
		request.addEventListener('error', () => reject(new Error('The upload could not reach the site')))
		request.addEventListener('abort', () => reject(new Error('The upload was stopped')))
		options.signal?.addEventListener('abort', () => request.abort(), { once: true })

		request.addEventListener('load', () => {
			if (request.status === 413) {
				reject(new Error('The site refused the file for its size'))
				return
			}
			if (request.status !== 200) {
				reject(new Error(serverMessage(request.responseText) ?? 'The upload failed'))
				return
			}
			options.onProgress?.(Math.min(1, (at.offset + slice.size) / Math.max(file.size, 1)))
			resolve(parse(request.responseText))
		})

		request.send(form)
	})
}

function parse(body: string): UploadedFile | null {
	try {
		return (JSON.parse(body).message as UploadedFile) ?? null
	} catch {
		return null
	}
}

/** What Frappe put in `_server_messages`, which is where it says why it refused. */
function serverMessage(body: string): string | null {
	try {
		const error = JSON.parse(body)
		const messages: string[] = JSON.parse(error._server_messages ?? '[]')
		const first = messages.map((message) => JSON.parse(message).message).find(Boolean)
		return first ?? error.exception ?? null
	} catch {
		return null
	}
}
