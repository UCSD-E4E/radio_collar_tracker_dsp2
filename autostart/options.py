'''RCT Payload Options
'''
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type

import yaml
from deprecated import deprecated


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
        'DSP_pingWidth': ParamEntry([float], lambda x: x > 0),
        'DSP_pingSNR': ParamEntry([float], lambda x: x > 0),
        'DSP_pingMax': ParamEntry([float], lambda x: x > 1),
        'DSP_pingMin': ParamEntry([float], lambda x: 0 < x < 1),
        'GPS_mode': ParamEntry([str], lambda x: x in ['true', 'false']),
        'GPS_device': ParamEntry([str]),
        'GPS_baud': ParamEntry([int], lambda x: x > 0),
        'TGT_frequencies': ParamEntry([list]),
        'SYS_autostart': ParamEntry([str], lambda x: x in ['true', 'false']),
        'SYS_outputDir': ParamEntry([str]),
        'SDR_samplingFreq': ParamEntry([int], lambda x: x > 0),
        'SDR_centerFreq': ParamEntry([int], lambda x: x > 0),
        'SDR_gain': ParamEntry([int, float]),
        'SYS_network': ParamEntry([str], None, str),
        'SYS_wifiMonitorInterval': ParamEntry([int], None, int),
        'SYS_heartbeat_period': ParamEntry([int], lambda x: x > 0),
    }

    def __init__(self, *,
                 config_path: Path = Path('/usr/local/etc/rct_config')):
        self._config_file = config_path
        self.options = list(self.param_fn_table.keys())
        self._params: Dict[str, Any] = {}
        self.loadParams()

    @deprecated
    def get_var(self, var: str) -> Any:
        """Gets the specified variable

        Args:
            var (str): Variable key

        Returns:
            Any: Variable value
        """
        retval = []
        with open(self._config_file, 'r', encoding='ascii') as var_file:
            config = yaml.safe_load(var_file)
            retval= config[var]
        return retval


    @deprecated
    def loadParams(self) -> None:
        self.load_params()

    def load_params(self) -> None:
        """Loads the parameters from disk
        """
        with open(self._config_file, 'r', encoding='ascii') as var_file:
            config = yaml.safe_load(var_file)
            for option in config:
                self._params[option] = config[option]

    @deprecated
    def getOption(self, option: str):
        return self.get_option(option=option)

    def get_option(self, option: str) -> Any:
        """Retrieves the specified option

        Args:
            option (str): Option key

        Returns:
            Any: Option value
        """
        return self._params[option]


    @deprecated
    def setOption(self, option, param):
        return self.set_option(option=option, param=param)

    def set_option(self, option: str, param: Any):
        """Sets the specified option value

        Args:
            option (str): Option key
            param (Any): New value
        """
        value = self.validate_option(option, param)

        self._params[option] = value

    @deprecated
    def setOptions(self, options: dict):
        self.set_options(options=options)



    def set_options(self, options: Dict[str, Any]):
        """Updates the current options from the specified dictionary

        Args:
            options (Dict[str, Any]): Options to update
        """
        for key, value in options.items():
            print('Option: ')
            print(key)
            print(value)

            value = self.validate_option(key, value)

            # update
            self._params[key] = value

    def validate_option(self, key: str, value: Any) -> Any:
        """Validates the option value

        Args:
            key (str): Option key
            value (Any): Value to be validated

        Raises:
            KeyError: Unknown key

        Returns:
            Any: Validated value
        """
        if key not in self.param_fn_table:
            raise KeyError('Unknown key')

        param_entry = self.param_fn_table[key]
        # validate first
        if param_entry.validation_fn:
            assert param_entry.validation_fn(value)

        # Transform
        if param_entry.transform_fn:
            value = param_entry.transform_fn(value)
        return value


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
            yaml.dump(self._params, var_file)

    @deprecated
    def getAllOptions(self):
        return self.get_all_options()

    def get_all_options(self) -> Dict[str, Any]:
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
