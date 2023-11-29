# coding=utf-8
"""
Implementation for:
- FilterValue class: a class that contains the filter conditions.
- FilterValueEncoder class: a JSON encoder for FilterValue objects.
"""

import json
from typing import Any

from UEVaultManager.tkgui.modules.functions import parse_callable
from UEVaultManager.tkgui.modules.functions_no_deps import create_uid
from UEVaultManager.tkgui.modules.types import FilterType


class FilterValue:
    """
    A class that contains the filter conditions.
    :param name: name of the filter
    :param ftype: type of the filter.
    :param value: various: value to search, function to call, list of values
    """

    def __init__(self, name: str, value, ftype=FilterType.STR):
        self.name: str = name
        self.value = value
        self._ftype: FilterType = ftype  # set type to str by default

    def __str__(self):
        return self.to_json()

    def __repr__(self):
        result = f'"{self.name}" '
        if self._ftype == FilterType.CALLABLE:
            func_name, func_params = parse_callable(self.value)
            result += f'result of {func_name}({",".join(func_params)})'
        elif self._ftype == FilterType.LIST:
            result += f'is in {self.value}'
        else:
            result += f'is a "{self._ftype.name}" equals to "{self.value}"'
        return result

    def __dict__(self):
        return self.to_dict()

    def to_dict(self) -> dict:
        """
        Export the properties of the FilterValue instance as a dictionary.
        :return: a dictionary containing the properties of the FilterValue instance.
        """
        return {'name': self.name, 'ftype': self._ftype.name, 'value': self.value}

    def to_json(self) -> str:
        """
        Export the properties of the FilterValue instance as a JSON string.
        :return: a JSON string representation of the FilterValue instance.
        """
        return json.dumps(self.to_dict())

    @classmethod
    def init(cls, data: dict) -> 'FilterValue':
        """
        Create a FilterValue object from a dictionnary.
        :param data: a dictionnary string representing a FilterValue object.
        :return: a FilterValue object created from the JSON string.
        """
        ftype_name = data.get('ftype', '')
        ftype = FilterType.from_name(ftype_name)
        value_str = data.get('value', '')
        if not isinstance(value_str, list):
            try:
                value_str = json.loads(value_str)
            except json.JSONDecodeError:
                pass
        return cls(name=data.get('name', 'f_' + create_uid()), ftype=ftype, value=value_str)

    @property
    def ftype(self) -> Any:
        """Get the type of the filter value. """
        return self._ftype

    @ftype.setter
    def ftype(self, value: Any):
        """Set the type of the filter value. """
        self._ftype = value


class FilterValueEncoder(json.JSONEncoder):
    """
    A JSON encoder for FilterValue objects.
    """

    def default(self, obj):
        """
        Encode a FilterValue object.
        :param obj: the object to encode.
        :return: the encoded object.
        """
        if isinstance(obj, FilterValue):
            return obj.to_dict()
        return super().default(obj)
