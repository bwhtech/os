/**
 * A GET call to a whitelisted method, for code outside Vue such as the React editor blocks.
 * The error has the message that the server shows.
 */
export async function getMethod<T>(method: string, params: Record<string, string> = {}): Promise<T> {
	const response = await fetch(`/api/method/${method}?${new URLSearchParams(params)}`, {
		headers: { Accept: 'application/json' },
	})
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
