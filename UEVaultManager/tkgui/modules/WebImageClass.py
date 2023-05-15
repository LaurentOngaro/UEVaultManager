# coding=utf-8
"""
Implementation for:
- WebImage: class to download an image from an url and get it as a PhotoImage
"""
from io import BytesIO

import requests
from PIL import ImageTk, Image

from UEVaultManager.tkgui.modules.functions import log_warning


class WebImage:
    """
    Class to download an image from an url and get it as a PhotoImage
    :param url: the url of the image to download
    """

    def __init__(self, url: str = None):
        # if no URL is given, return
        if url is None or url == '':
            return
        # initialize instance variables
        self.__image_pil = None
        self.__image_tk = None
        self.url = url
        try:
            # use requests to get the image content as bytes
            response = requests.get(url)
            # create a PIL.Image object from the bytes
            self.__image_pil = Image.open(BytesIO(response.content))
            # create a PhotoImage object from the PIL.Image
            self.__image_tk = ImageTk.PhotoImage(self.__image_pil)
        except Exception as error:
            # log a warning if image cannot be downloaded or opened
            log_warning(f'image could not be read from url {self.url}.\nError:{error}')

    def get(self) -> ImageTk.PhotoImage:
        """
        Get the downloaded image
        :return: the image
        """
        return self.__image_tk

    def get_resized(self, new_width: int, new_height: int) -> ImageTk.PhotoImage:
        """
        Get the downloaded image resized to the given size
        :param new_width: width of the resized image
        :param new_height: height of the resized image
        :return: the resized image
        """
        try:
            # resize the PIL.Image object in place
            self.__image_pil.thumbnail((new_width, new_height))
            # create a PhotoImage object from the resized PIL.Image
            self.__image_tk = ImageTk.PhotoImage(self.__image_pil)
        except Exception as error:
            # log a warning if image cannot be resized
            log_warning(f'Could not get resized image from url {self.url}.\nError:{error}')
        return self.__image_tk
