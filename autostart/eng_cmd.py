'''Engineering Command handlers
'''
import logging
from typing import Callable, Dict

engr_cmd_map: Dict[str, Callable] = {}

def handle_engr_cmd(command_word: str, **kwargs):
    """Handle engineering commands

    Args:
        command_word (str): Command Word
    """
    logger = logging.getLogger('Engineering Commands')
    if command_word not in engr_cmd_map:
        return
    engr_fn = engr_cmd_map[command_word]
    try:
        logger.info('Executing %s', engr_fn.__name__)
        engr_fn(**kwargs)
    except Exception as exc: # pylint: disable=broad-except
        # log exception and carry on
        logger.exception('Exception during engineering command: %s', exc)
