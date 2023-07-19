'''Tests that options serialization works
'''
from pathlib import Path
from typing import Tuple

from autostart.options import RCTOpts, Options


def test_option(test_env: Tuple[Path]):
    config_path = test_env[0]
    options = RCTOpts.get_instance(config_path)

    assert isinstance(options.get_option(Options.GCS_SPEC), str)