import type { BlogComment, BlogPost, BlogPostRow } from '@/types'

const BLOG_URL = 'https://bwh.tech/blog'

/** '' shows all comments. */
export type CommentStatus = '' | 'visible' | 'hidden'

/** A post with the comments that match the filters. Posts with no match are left out. */
export interface CommentGroupData {
	post: BlogPost
	comments: BlogComment[]
}

/** One group for each post that has comments. The comments are newest first, so the groups are too. */
export function groupByPost(comments: BlogComment[], posts: BlogPostRow[]): BlogPost[] {
	const postsById = new Map(posts.map((post) => [post.name, post]))
	const groups = new Map<string, BlogPost>()
	for (const comment of comments) {
		let group = groups.get(comment.post)
		if (!group) {
			const post = postsById.get(comment.post)
			group = {
				post_id: comment.post,
				// The feed had no title when OS made the post, for example for a draft.
				title: post?.title || comment.post,
				url: `${BLOG_URL}/${comment.post}/`,
				likes: post?.likes ?? 0,
				comments: [],
			}
			groups.set(comment.post, group)
		}
		group.comments.push(comment)
	}
	return [...groups.values()]
}

export function filterGroups(posts: BlogPost[], status: CommentStatus, search: string): CommentGroupData[] {
	const query = search.trim().toLowerCase()
	return posts
		.map((post) => ({
			post,
			comments: post.comments.filter(
				(comment) => matchesStatus(comment, status) && matchesSearch(comment, query),
			),
		}))
		.filter((group) => group.comments.length)
}

function matchesStatus(comment: BlogComment, status: CommentStatus) {
	if (status === 'visible') return !comment.hidden
	if (status === 'hidden') return Boolean(comment.hidden)
	return true
}

function matchesSearch(comment: BlogComment, query: string) {
	if (!query) return true
	return [comment.commenter_name, comment.email, comment.body].some((text) =>
		text.toLowerCase().includes(query),
	)
}
