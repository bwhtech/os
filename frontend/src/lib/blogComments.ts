import type { BlogComment, BlogPost } from '@/types'

/** '' shows all comments. */
export type CommentStatus = '' | 'visible' | 'hidden'

/** A post with the comments that match the filters. Posts with no match are left out. */
export interface CommentGroupData {
	post: BlogPost
	comments: BlogComment[]
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
	if (status === 'hidden') return comment.hidden
	return true
}

function matchesSearch(comment: BlogComment, query: string) {
	if (!query) return true
	return [comment.name, comment.email, comment.body].some((text) => text.toLowerCase().includes(query))
}
