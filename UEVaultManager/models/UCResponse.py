# coding=utf-8
"""
Implementation for:
- UCResponse: Response object for the undetected Chrome driver.
"""
import json

from requests import PreparedRequest, Response


class UCResponse(Response):
    """
    Response object for the undetected Chrome driver.

    Overrided to change some attributes and methods
    """

    def __init__(self):
        """
        NOTE:
            Response properties are:
            _content
            status_code
            headers
            url
            history
            encoding
            reason
            cookies
            elapsed
            request
        """
        super().__init__()
        self._content = None
        self.raw = ''
        self.reason = ''
        self.url = ''
        self.request = PreparedRequest()
        self.connection = None
        self.encoding = 'utf-8'
        self.status_code = 403

    def json(self, **kwargs):
        """
        Return the json content of the response.
        """
        try:
            # the following could raise a json.JSONDecodeError if the content is already a string
            json_content = super().json(**kwargs)
        except json.JSONDecodeError:
            json_content = json.loads(self._content)
        return json_content

    @property
    def content(self):
        """ Return the content of the response. """
        return self._content

    @content.setter
    def content(self, value):
        """ Setter for content. """
        self._content = value
