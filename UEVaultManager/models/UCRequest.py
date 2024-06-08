# coding=utf-8
"""
Implementation for:
- UCResponse: Response object for the undetected Chrome driver.
"""

from UEVaultManager.models import UCResponse
from UEVaultManager.tkgui.modules.types import UCRequestType


class UCRequest:
    """
    Store some data use to make a request using an undetected Chrome driver.
    """

    def __init__(self):
        self.response: UCResponse = None
        self.params = None
        self.request_type: UCRequestType = UCRequestType.NORMAL
