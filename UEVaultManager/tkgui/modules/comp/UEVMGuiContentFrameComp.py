# coding=utf-8
"""
Implementation for:
- UEVMGuiContentFrame: a container for a datatable widget for the UEVMGui Class.
"""
import ttkbootstrap as ttk


class UEVMGuiContentFrame(ttk.Frame):
    """
    A container for a datatable widget for the UEVMGui Class.
    :param container: The parent container.
    """

    def __init__(self, container):
        if container is None:
            raise ValueError('container must be None')
        super().__init__(container)

        self.container = container
