from app.services.draft_preview import can_preview_drafts


def topic_statuses(user):
    return ('inherited','published','draft','review') if can_preview_drafts(user) else ('inherited','published')


def topic_allowed(topic,user):
    return topic is not None and topic.publication_status in topic_statuses(user)
