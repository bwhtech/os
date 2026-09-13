from bwh_os.mailing.newsletter_archive import public_issues

# A publish in OS must show at once.
no_cache = 1


def get_context(context):
	context.title = "Newsletter"
	context.issues = public_issues()
