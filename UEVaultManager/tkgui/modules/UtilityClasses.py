# noinspection DuplicatedCode
class SaferDict(dict):
    """
    A dictionary subclass that provides a safer alternative to handle non-existing keys.
    It returns None or the specified default value when accessing non-existing keys, rather than raising a KeyError.
    """

    def __getitem__(self, key):
        """
        Returns the value associated with the given key.
        If the key does not exist, returns None.
        """
        try:
            return super().__getitem__(key)
        except KeyError:
            return None

    def get(self, key, default=None):
        """
        Returns the value associated with the given key.
        If the key does not exist, returns the specified default value or None if no default value is provided.
        """
        return super().get(key, default)

    def __getattr__(self, key):
        """
        Returns the value associated with the given key using dot notation.
        If the key does not exist, returns None.
        """
        return self.get(key)

    def __delattr__(self, key):
        """
        Deletes the key-value pair associated with the given key using dot notation.
        If the key does not exist, does nothing and does not raise an error.
        """
        try:
            del self[key]
        except KeyError:
            pass

    def __setattr__(self, key, value):
        """
        Sets the value associated with the given key using dot notation.
        """
        self[key] = value

    def copy_from(self, source):
        """
        Copies the content of the given source dictionary into the SaferDict.
        If the source is not a dictionary, raises a TypeError.
        """
        if not isinstance(source, dict):
            raise TypeError("source must be a dictionary")
        self.clear()
        for key, value in source.items():
            self[key] = value
