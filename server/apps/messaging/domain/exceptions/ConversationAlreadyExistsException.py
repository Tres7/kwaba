class ConversationAlreadyExistsException(Exception):
    """Raised by the persistence when a thread (listing, traveller) already exists (concurrent creation)."""
    pass
