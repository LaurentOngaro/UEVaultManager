# coding=utf-8
"""
Implementation for:
- FilterValue class: a class that contains the filter conditions.
- FilterValueEncoder class: a JSON encoder for FilterValue objects.
"""

import json
from typing import Any

from UEVaultManager.models.csv_sql_fields import get_field_type


class FilterValue:
    """
    A class that contains the filter conditions.
    :param col_name: name of the coliumn to filter or string literal 'callable'
    :param value: value to filter or function to call if col_name is 'callable'.
    :param use_or: wether to use an OR condition with the PREVIOUS filter.
    """

    def __init__(self, col_name: str, value: Any, use_or: bool = False, pos: int = -1):
        self.col_name: str = col_name
        self.value: Any = value
        self.use_or: bool = use_or
        self.pos: int = pos
        if col_name == 'callable':
            self._ftype = 'callable'  # must be a literal string
        else:
            ftype = get_field_type(col_name)
            self._ftype: type = ftype.cast_to_type() if ftype else str

    def __str__(self):
        return self.to_json()

    def __repr__(self):
        result = f'"{self.col_name}" of type "{self._ftype.__name__}" is/contains "{self.value}"'
        result += f' at pos {self.pos}' if self.pos >= 0 else ''
        result += ' (OR)' if self.use_or else ' (AND)'
        return result

    def __dict__(self):
        return self.to_dict()

    def to_dict(self) -> dict:
        """
        Export the properties of the FilterValue instance as a dictionary.
        :return: a dictionary containing the properties of the FilterValue instance.
        """
        return {
            'col_name': self.col_name,
            'ftype': self._ftype.__name__ if self._ftype != 'callable' else 'callable',  # 'callable' is a literal string
            'value': self.value,
            'pos': self.pos,
            'use_or': self.use_or
        }

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
        return cls(data.get('col_name', ''), data.get('value', ''), data.get('use_or', False), data.get('pos', -1))

    @property
    def ftype(self) -> type:
        """Get the type of the filter value. """
        return self._ftype


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
