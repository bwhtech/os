import { useEffect, useState, type FormEvent } from 'react'
import { Node, nodePasteRule, type JSONContent } from '@tiptap/core'
import { NodeViewWrapper, ReactNodeViewRenderer, type ReactNodeViewProps } from '@tiptap/react'
import { EmailNode } from '@react-email/editor/core'
import { ImageIcon, PanelBottomIcon, defaultSlashCommands, type SlashCommandItem } from '@react-email/editor/ui'
import { FOOTER_ATTRIBUTE, loadFooterHtml } from '@/lib/emailFooter'
import { postMethod } from '@/lib/serverMethod'

/** Custom blocks for every email in OS. See slice 13 in specs/01-email-list.md. */
export const blockExtensions = () => [youTubeVideoExtension(), footerExtension()]

export const BLOCK_NODES = ['youtubeVideo', 'emailFooter']

/**
 * EmailEditor always renders its own slash menu, and that menu reads defaultSlashCommands. Adding the
 * blocks to that list is the only way in without a copy of EmailEditor.
 */
export function addBlockSlashCommands() {
	for (const item of SLASH_COMMANDS) {
		if (!defaultSlashCommands.includes(item)) defaultSlashCommands.push(item)
	}
}

const SLASH_COMMANDS: SlashCommandItem[] = [
	{
		title: 'YouTube video',
		description: 'A thumbnail that links to the video',
		icon: <ImageIcon size={20} />,
		category: 'Layout',
		searchTerms: ['youtube', 'video'],
		command: ({ editor, range }) => {
			editor.chain().focus().deleteRange(range).insertContent({ type: 'youtubeVideo' }).run()
		},
	},
	{
		title: 'Footer',
		description: 'Social links, company details, and the unsubscribe link',
		icon: <PanelBottomIcon size={20} />,
		category: 'Layout',
		searchTerms: ['footer', 'unsubscribe', 'social', 'address'],
		command: ({ editor, range }) => {
			editor.chain().focus().deleteRange(range).insertContent({ type: 'emailFooter' }).run()
		},
	},
]

/* YouTube video */

const YOUTUBE_URL =
	/https?:\/\/(?:www\.|m\.)?(?:youtube\.com\/(?:watch\?\S*v=|shorts\/|live\/)|youtu\.be\/)[\w-]{11}\S*/g

interface Video {
	video_id: string
	url: string
	title: string
	thumbnail: string
}

function youTubeVideoExtension() {
	const node = Node.create({
		name: 'youtubeVideo',
		group: 'block',
		atom: true,
		draggable: true,

		addAttributes() {
			return {
				url: { default: null },
				videoId: { default: null },
				title: { default: null },
				thumbnail: { default: null },
			}
		},

		parseHTML() {
			return [{ tag: 'div[data-youtube-video]' }]
		},

		renderHTML({ HTMLAttributes }) {
			return ['div', { 'data-youtube-video': '', ...HTMLAttributes }]
		},

		addNodeView() {
			return ReactNodeViewRenderer(YouTubeVideoView)
		},

		// A YouTube link pasted on its own becomes a video block.
		addPasteRules() {
			return [nodePasteRule({ find: YOUTUBE_URL, type: this.type, getAttributes: (match) => ({ url: match[0] }) })]
		},
	})

	return EmailNode.from(node, ({ node }) => <VideoEmail node={node} />)
}

/** The thumbnail has the play button drawn in, because many email clients drop overlays. */
function VideoEmail({ node }: { node: JSONContent }) {
	const { url, title, thumbnail } = node.attrs ?? {}
	if (!url || !thumbnail) return null
	return (
		<table role="presentation" width="100%" cellPadding={0} cellSpacing={0} border={0} style={{ margin: '16px 0' }}>
			<tbody>
				<tr>
					<td>
						<a href={url} target="_blank" style={{ display: 'block', textDecoration: 'none' }}>
							<img
								src={thumbnail}
								alt={title ?? 'YouTube video'}
								width="100%"
								style={{ display: 'block', width: '100%', height: 'auto', border: 0, borderRadius: 8 }}
							/>
						</a>
						{title && (
							<a
								href={url}
								target="_blank"
								style={{ display: 'block', marginTop: 8, fontWeight: 600, color: 'inherit', textDecoration: 'none' }}
							>
								{title}
							</a>
						)}
					</td>
				</tr>
			</tbody>
		</table>
	)
}

function YouTubeVideoView({ node, updateAttributes, selected }: ReactNodeViewProps) {
	const [link, setLink] = useState<string>(node.attrs.url ?? '')
	const [loading, setLoading] = useState(false)
	const [error, setError] = useState<string | null>(null)

	const load = async (url: string) => {
		setLoading(true)
		setError(null)
		try {
			const video = await postMethod<Video>('bwh_os.mailing.api.get_youtube_video', { url })
			updateAttributes({ url: video.url, videoId: video.video_id, title: video.title, thumbnail: video.thumbnail })
		} catch (err) {
			setError((err as Error).message)
		} finally {
			setLoading(false)
		}
	}

	// A pasted link has only the URL, so the block looks up the video once.
	useEffect(() => {
		if (node.attrs.url && !node.attrs.videoId) load(node.attrs.url)
	}, [])

	const submit = (event: FormEvent) => {
		event.preventDefault()
		if (link.trim()) load(link.trim())
	}

	return (
		<NodeViewWrapper className={`email-block${selected ? ' is-selected' : ''}`} data-drag-handle="">
			{node.attrs.videoId ? (
				<VideoEmail node={node.toJSON()} />
			) : (
				<form className="email-block-form" contentEditable={false} onSubmit={submit}>
					<label className="email-block-label">YouTube video</label>
					<div className="email-block-row">
						<input
							value={link}
							onChange={(event) => setLink(event.target.value)}
							placeholder="Paste a YouTube link"
							disabled={loading}
							autoFocus
						/>
						<button type="submit" disabled={loading || !link.trim()}>
							{loading ? 'Adding…' : 'Add video'}
						</button>
					</div>
					{error && <p className="email-block-error">{error}</p>}
				</form>
			)}
		</NodeViewWrapper>
	)
}

/* Footer */

function footerExtension() {
	const node = Node.create({
		name: 'emailFooter',
		group: 'block',
		atom: true,
		draggable: true,

		parseHTML() {
			return [{ tag: `div[${FOOTER_ATTRIBUTE}]` }]
		},

		renderHTML() {
			return ['div', { [FOOTER_ATTRIBUTE]: '' }]
		},

		addNodeView() {
			return ReactNodeViewRenderer(FooterView)
		},
	})

	// The server fills the marker when it sends. See emails.add_footer.
	return EmailNode.from(node, () => <div {...{ [FOOTER_ATTRIBUTE]: '' }} />)
}

function FooterView({ selected }: ReactNodeViewProps) {
	const [html, setHtml] = useState<string | null>(null)
	const [error, setError] = useState<string | null>(null)

	useEffect(() => {
		loadFooterHtml()
			.then(setHtml)
			.catch((err: Error) => setError(err.message))
	}, [])

	return (
		<NodeViewWrapper className={`email-block${selected ? ' is-selected' : ''}`} data-drag-handle="">
			<span className="email-block-badge" contentEditable={false}>
				Footer from Settings
			</span>
			{error ? (
				<p className="email-block-error">{error}</p>
			) : (
				<div contentEditable={false} dangerouslySetInnerHTML={{ __html: html ?? '' }} />
			)}
		</NodeViewWrapper>
	)
}
