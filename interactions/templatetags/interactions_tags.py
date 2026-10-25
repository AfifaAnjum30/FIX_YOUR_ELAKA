from django import template

from interactions.forms import CommentForm

register = template.Library()


@register.inclusion_tag(
    "interactions/includes/interaction_panel.html", takes_context=True
)
def interaction_panel(context, report):
    """Renders vote buttons, net score and comments for a report."""
    request = context["request"]
    user = request.user

    user_vote = None
    if user.is_authenticated:
        user_vote = (
            report.votes.filter(user=user).values_list("vote_value", flat=True).first()
        )

    return {
        "report": report,
        "user": user,
        "request": request,
        "csrf_token": context.get("csrf_token"),   # needed for the forms
        "summary": report.votes.summary(),         # upvotes / downvotes / score
        "user_vote": user_vote,                    # 1, -1 or None
        "comments": report.comments.select_related("user"),
        "comment_form": CommentForm(),
    }