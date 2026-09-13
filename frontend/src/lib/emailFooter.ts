import { getMethod } from '@/lib/getMethod'

/**
 * The Footer block. The editor saves it as an empty marker, and the server puts the company footer
 * from Mailing Settings in its place when it sends. Keep the marker in step with FOOTER_BLOCK in
 * bwh_os/mailing/emails.py.
 */
export const FOOTER_ATTRIBUTE = 'data-email-footer'

const FOOTER_MARKER = new RegExp(`<div[^>]*\\b${FOOTER_ATTRIBUTE}\\b[^>]*>\\s*</div\\s*>`, 'gi')

let footerHtml: Promise<string> | null = null

/** The footer as the server renders it, with a sample unsubscribe link. Loaded once for each page. */
export function loadFooterHtml(): Promise<string> {
	footerHtml ??= getMethod<string>('bwh_os.mailing.api.get_email_footer').catch((error) => {
		footerHtml = null
		throw error
	})
	return footerHtml
}

/** Put the footer in place of the Footer block, so the preview shows what a reader gets. */
export async function fillFooter(html: string): Promise<string> {
	if (!html.match(FOOTER_MARKER)) return html
	// The preview still shows the email when the footer does not load.
	const footer = await loadFooterHtml().catch(() => '')
	return html.replace(FOOTER_MARKER, () => footer)
}
