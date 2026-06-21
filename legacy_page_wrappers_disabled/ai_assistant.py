"""Compatibility page wrapper. Existing AI logic remains in tabs.ai_assistant_lite."""
def show():
    from tabs.ai_assistant_lite import show as _show
    return _show()
