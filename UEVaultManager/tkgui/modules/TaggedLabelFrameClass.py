import tkinter
from tkinter import ttk


class TaggedLabelFrame(ttk.LabelFrame):
    """
    A custom LabelFrame widget that allows child widgets to be identified by tags.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tagged_children = {}

    def add_child(self, child: tkinter.Widget, tag: str):
        """
        Adds a child widget to the LabelFrame and associates it with the given tag.
        """
        self._tagged_children[tag] = child

    def get_child_by_tag(self, tag: str) -> tkinter.Widget:
        """
        Returns the child widget associated with the given tag.
        """
        return self._tagged_children.get(tag, None)

    def get_tagged_children(self) -> dict:
        """
        Returns the child widget associated with the given tag.
        """
        return self._tagged_children
