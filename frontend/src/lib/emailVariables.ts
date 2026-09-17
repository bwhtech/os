/**
 * Values that the server puts in an email when it sends. Keep the keys and fallbacks in step with
 * VARIABLES in bwh_os/mailing/email_variables.py.
 */
export interface EmailVariable {
	key: string
	label: string
	description: string
	/** Used when the value is empty */
	fallback?: string
	/** Shown in the preview */
	sample: string
}

/** What to type for this variable, which is not its label. */
export function token(variable: EmailVariable): string {
	return `{{ ${variable.key} }}`
}

/** The tooltip text of a variable. It names the token, because a link field has no chips. */
export function describe(variable: EmailVariable): string {
	const fallback = variable.fallback ? ` When empty: “${variable.fallback}”.` : ''
	return `${token(variable)} — ${variable.description}${fallback}`
}

const FIRST_NAME: EmailVariable = {
	key: 'first_name',
	label: 'First name',
	description: "The subscriber's first name.",
	fallback: 'there',
	sample: 'Priya',
}

const EMAIL: EmailVariable = {
	key: 'email',
	label: 'Email',
	description: "The subscriber's email address.",
	sample: 'priya@example.com',
}

const CONFIRM_URL: EmailVariable = {
	key: 'confirm_url',
	label: 'Confirm link',
	description: 'The link that confirms the subscription. Use it as a button link.',
	sample: 'https://bwh.tech/confirm',
}

const DOWNLOAD_URL: EmailVariable = {
	key: 'download_url',
	label: 'Download link',
	description: 'The link to the lead magnet file. Use it as a button link.',
	sample: 'https://bwh.tech/download',
}

const LEAD_MAGNET: EmailVariable = {
	key: 'lead_magnet',
	label: 'Lead magnet',
	description: 'The title of the lead magnet.',
	sample: 'The Missing Frappe Manual',
}

export const NEWSLETTER_VARIABLES = [FIRST_NAME, EMAIL]
export const CONFIRM_VARIABLES = [FIRST_NAME, EMAIL, CONFIRM_URL]
export const WELCOME_VARIABLES = [FIRST_NAME, EMAIL, DOWNLOAD_URL, LEAD_MAGNET]

// Also matches a link, where the editor URL-encodes the braces and spaces.
const VARIABLE_PATTERN = /(?:\{\{|%7B%7B)(?:\s|%20)*([a-z_]+)(?:\s|%20)*(?:\}\}|%7D%7D)/gi

/** Put the sample values in the HTML, so the preview shows what a reader gets. */
export function fillSamples(html: string, variables: EmailVariable[]): string {
	const samples = new Map(variables.map((variable) => [variable.key, variable.sample]))
	return html.replace(VARIABLE_PATTERN, (match, key: string) => escapeHtml(samples.get(key) ?? match))
}

function escapeHtml(text: string) {
	return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}
