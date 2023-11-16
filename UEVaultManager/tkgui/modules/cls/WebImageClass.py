# coding=utf-8
"""
Implementation for:
- WebImage: class to download an image from an url and get it as a PhotoImage.
"""
from io import BytesIO

import requests
from PIL import Image, ImageTk

from UEVaultManager.tkgui.modules.functions import log_warning


class WebImage:
    """
    Class to download an image from an url and get it as a PhotoImage.
    :param url: url of the image to download.
    """

    def __init__(self, url: str = None):
        self.url = url
        if url:
            try:
                response = requests.get(url, timeout=(4, 4))
                self.__image_pil = Image.open(BytesIO(response.content))
                self._image_tk = ImageTk.PhotoImage(self.__image_pil)
            except Exception as error:
                log_warning(f'image could not be read from url {url}.\nError:{error!r}')

    def get(self) -> ImageTk.PhotoImage:
        """
        Get the downloaded image.
        :return: image.
        """
        return self._image_tk

    def get_resized(self, new_width: int, new_height: int) -> ImageTk.PhotoImage:
        """
        Get the downloaded image resized to the given size.
        :param new_width: width of the resized image.
        :param new_height: height of the resized image.
        :return: resized image.
        """
        try:
            # resize the PIL.Image object in place
            self.__image_pil.thumbnail((new_width, new_height))
            # create a PhotoImage object from the resized PIL.Image
            self._image_tk = ImageTk.PhotoImage(self.__image_pil)
        except Exception as error:
            # log a warning if image can not be resized
            log_warning(f'Could not get resized image from url {self.url}.\nError:{error!r}')
        return self._image_tk
