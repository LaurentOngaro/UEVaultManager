# coding=utf-8
"""
Implementation for:
- SaferDict: a dictionary subclass that provides a safer alternative to handle non-existing keys.
"""


class SaferDict(dict):
    """
    A dictionary subclass that provides a safer alternative to handle non-existing keys.
    It returns None or the specified default value when accessing non-existing keys, rather than raising a KeyError.
    """

    def __getitem__(self, key):
        """
        Return the value associated with the given key.
        If the key does not exist, returns None.
        :param key: the key to get.
        """
        return super().get(key, None)

    def __getattr__(self, key):
        """
        Return the value associated with the given key using dot notation.
        If the key does not exist, returns None.
        :param key: the key to get.
        """
        return super().get(key, None)

    def __delattr__(self, key):
        """
        Delete the key-value pair associated with the given key using dot notation.
        If the key does not exist, does nothing and does not raise an error.
        :param key: the key to delete.
        """
        self.pop(key, None)

    def __setattr__(self, key, value):
        """
        Set the value associated with the given key using dot notation.
        :param key: the key to set.
        """
        self[key] = value

    def get(self, key: str, default=None):
        """
        Return the value associated with the given key.
        If the key does not exist, returns the specified default value or None if no default value is provided.
        :param key: the key to get.
        :param default: the default value to return if the key doesn't exist.
        """
        return super().get(key, default)

    def copy_from(self, source: dict):
        """
        Copie the content of the given source dictionary into the SaferDict.
        :param source: the source dictionary to copy from.
        """
        if not isinstance(source, dict):
            raise TypeError("source must be a dictionary")
        self.clear()
        self.update({k: v for k, v in source.items()})
