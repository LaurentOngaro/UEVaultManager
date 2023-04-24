from io import BytesIO
from urllib.parse import quote_plus
from urllib.request import urlopen
from UEVaultManager.tkgui.modules.functions import log_warning
from PIL import ImageTk, Image


class WebImage:

    def __init__(self, url):
        if url is None or url == '':
            return
        self.__image_pil = None
        self.__image_tk = None
        self.url = url
        encoded_url = quote_plus(url, safe='/:&')
        try:
            my_page = urlopen(encoded_url)
            my_picture = BytesIO(my_page.read())
            self.__image_pil = Image.open(my_picture)
            self.__image_tk = ImageTk.PhotoImage(self.__image_pil)
        except Exception as error:
            log_warning(f'image could not be read from url {self.url}.\nError:{error}')

    def get(self):
        return self.__image_tk

    def get_resized(self, new_width, new_height):
        try:
            self.__image_pil.thumbnail((new_width, new_height))
            self.__image_tk = ImageTk.PhotoImage(self.__image_pil)
        except Exception as error:
            log_warning(f'Could notre get resized image from url {self.url}.\nError:{error}')
        return self.__image_tk
