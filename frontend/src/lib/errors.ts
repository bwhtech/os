import { FrappeResponseError } from 'frappe-ui'

/** frappe-ui prefixes the message with the exception type, e.g. "DuplicateEntryError: ". */
export function errorMessage(error: Error | null | undefined): string {
	if (!error) return ''
	if (!(error instanceof FrappeResponseError)) return error.message
	return error.message.replace(`${error.type}: `, '')
}
