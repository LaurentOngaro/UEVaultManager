from io import BytesIO
from PIL import Image, ImageTk

import tkinter as tk
from urllib.request import urlopen

import os


class WebImage:

    def __init__(self, url):
        self.__image_pil = None
        self.__image_tk = None
        self.url = url
        try:
            my_page = urlopen(self.url)
            my_picture = BytesIO(my_page.read())
            self.__image_pil = Image.open(my_picture)
            self.__image_tk = ImageTk.PhotoImage(self.__image_pil)
        except Exception as e:
            print(f'image could not be read from url {self.url}.\nError:{e}')

    def get(self):
        return self.__image_tk

    def get_resized(self, new_width, new_height):
        try:
            self.__image_pil.thumbnail((new_width, new_height))
            self.__image_tk = ImageTk.PhotoImage(self.__image_pil)
        except Exception as e:
            print(f'Could notre get resized image from url {self.url}.\nError:{e}')
        return self.__image_tk


root = tk.Tk()
root.title("Show image from URL")

image = WebImage("https://beccaboosandkimblebees.files.wordpress.com/2013/02/tumblr_mhm8uaxf731rrufwao1_500_large.jpg")
tk_img = image.get()
resized_img = image.get_resized(50, 50)

current_working_directory = os.path.dirname(os.getcwd())
image_path = os.path.join(current_working_directory, 'UEVaultManager/assets/UEVM_200x200.png')
image_path = os.path.normpath(image_path)
test_img = tk.PhotoImage(file=image_path)

# put the image on a typical widget
label = tk.Label(root, image=tk_img)
label.pack(padx=5, pady=5)

# put the image on a typical widget
label = tk.Label(root, image=resized_img)
label.pack(padx=5, pady=5)

root.mainloop()
