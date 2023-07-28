'''RCT Payload Options
'''
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type

import yaml
from deprecated import deprecated
from RCTComms.options import Options, validate_option


@dataclass
class ParamEntry:
    """Parameter Validation dataclass
    """
    type_list: List[Type]
    validation_fn: Optional[Callable[[Any], bool]] = None
    transform_fn: Optional[Callable[[Any], Any]] = None

class RCTOpts:
    """Global options object
    """

    param_fn_table: Dict[str, ParamEntry] = {
    }

    def __init__(self, *,
                 config_path: Path = Path('/usr/local/etc/rct_config')):
        self.__log = logging.getLogger('Opts')
        self._config_file = config_path
        self._params: Dict[Options, Any] = {}
        self.loadParams()

    @deprecated
    def loadParams(self) -> None:
        self.load_params()

    def load_params(self) -> None:
        """Loads the parameters from disk
        """
        with open(self._config_file, 'r', encoding='ascii') as var_file:
            config: Dict[str, Any] = yaml.safe_load(var_file)
            for option in config:
                self._params[Options(option)] = config[option]
                self.__log.info('Discovered %s as %s', option, str(config[option]))

    def get_option(self, option: Options) -> Any:
        """Retrieves the specified option

        Args:
            option (str): Option key

        Returns:
            Any: Option value
        """
        return self._params[option]


    def set_option(self, option: Options, param: Any):
        """Sets the specified option value

        Args:
            option (str): Option key
            param (Any): New value
        """
        value = validate_option(option, param)

        self._params[option] = value


    def set_options(self, options: Dict[Options, Any]):
        """Updates the current options from the specified dictionary

        Args:
            options (Dict[Options, Any]): Options to update
        """
        for key, value in options.items():

            value = validate_option(key, value)

            # update
            self._params[key] = value




    @deprecated
    def writeOptions(self):
        self.write_options()

    def write_options(self):
        """Writes the current options to disk
        """
        backups = self._config_file.parent.glob('*.bak')
        if len(backups) > 0:
            backup_numbers = [path.stem.lstrip('rct_config')
                              for path in backups]
            backup_numbers = [int(number)
                              for number in backup_numbers
                              if number != '']
            next_number = max(backup_numbers) + 1
        else:
            next_number = 1

        new_name = f'{self._config_file.stem}{next_number}.bak'
        new_path = self._config_file.parent.joinpath(new_name)
        self._config_file.rename(new_path)

        with open(self._config_file, 'w', encoding='ascii') as var_file:
            data = {key.name:value for key, value in self._params.items()}
            yaml.dump(data, var_file)

    @deprecated
    def getAllOptions(self):
        return self.get_all_options()

    def get_all_options(self) -> Dict[Options, Any]:
        """Retrieves all options

        Returns:
            Dict[str, Any]: All option values
        """
        return self._params

    @deprecated
    def getCommsOptions(self):
        return self.get_comms_options()

    @deprecated
    def get_comms_options(self):
        return self._params
    
    _option_map: Dict[Path, RCTOpts] = {}
    @classmethod
    def get_instance(cls, path: Path) -> RCTOpts:
        if path not in cls._option_map:
            cls._option_map[path] = RCTOpts(config_path=path)
        return cls._option_map[path]
