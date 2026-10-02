def snapshot(current_faults=0, unread=0, paused=False, saved_gaps=0):
    """Return live ingestion status and retained coverage gaps separately."""
    state = ('stopped' if paused else
             'error' if current_faults or saved_gaps else
             'loading' if unread else 'ready')
    return {'state': state, 'saved_gaps': saved_gaps}
