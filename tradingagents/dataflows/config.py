from tradingagents.config import settings

def get_config():
    """
    Returns the current configuration.
    """
    return settings.model_dump()

def set_config(new_config):
    """
    Updates the configuration.
    """
    global settings
    # This is not ideal, but it's the simplest way to update the settings
    # without a major refactor of the application.
    for key, value in new_config.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
