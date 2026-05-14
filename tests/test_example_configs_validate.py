from pathlib import Path

from ascon_arch.config import ImplementationConfig
from ascon_arch.validation import validate_config


def test_all_checked_in_example_configs_validate() -> None:
    config_paths = sorted(Path("configs").glob("**/*.json"))
    assert config_paths
    for config_path in config_paths:
        validate_config(ImplementationConfig.read_json(config_path))
