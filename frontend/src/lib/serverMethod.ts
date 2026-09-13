/**
 * Calls to whitelisted methods, for code outside Vue such as the React editor blocks.
 * The error has the message that the server shows.
 */
export function getMethod<T>(method: string, params: Record<string, string> = {}): Promise<T> {
	return request<T>(`/api/method/${method}?${new URLSearchParams(params)}`, { method: 'GET' })
}

/** Use POST for a method that writes. Frappe does not commit a GET request. */
export function postMethod<T>(method: string, params: Record<string, string> = {}): Promise<T> {
	return request<T>(`/api/method/${method}`, {
		method: 'POST',
		body: new URLSearchParams(params),
		headers: { 'X-Frappe-CSRF-Token': window.csrf_token ?? '' },
	})
}

async function request<T>(url: string, init: RequestInit): Promise<T> {
	const response = await fetch(url, { ...init, headers: { Accept: 'application/json', ...init.headers } })
	const body = await response.json().catch(() => ({}))
	if (!response.ok) throw new Error(serverMessage(body) ?? 'Something went wrong')
	return body.message as T
}

function serverMessage(body: { _server_messages?: string; exception?: string }): string | null {
	try {
		const messages = JSON.parse(body._server_messages ?? '[]') as string[]
		if (messages.length) return JSON.parse(messages[0]).message
	} catch {
		// Fall back to the exception text
	}
	return body.exception?.replace(/^[\w.]+:\s*/, '') ?? null
}
