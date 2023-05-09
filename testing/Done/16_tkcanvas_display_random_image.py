import tkinter as tk
import requests
from PIL import Image, ImageTk
import io
import random


def get_random_number():
    """
    Generate a random number between 100 and 200.

    Returns:
        int: A random integer between 100 and 200, inclusive.
    """
    return random.randint(100, 300)


def get_random_image_url():
    """
    Generate a random image URL from a website.

    Returns:
        str: A random image URL.
    """
    return f'https://picsum.photos/{get_random_number()}'


def download_image(url):
    """
    Download an image from the given URL.

    Args:
        url (str): The URL of the image.

    Returns:
        Image: An Image object containing the downloaded image data.
    """
    response = requests.get(url)
    image_data = response.content
    image = Image.open(io.BytesIO(image_data))
    return image


def display_image(canvas, image):
    """
    Display an image on a tkinter Canvas widget.

    Args:
        canvas (tk.Canvas): The Canvas widget to display the image on.
        image (Image): The Image object to display.
    """
    tk_image = ImageTk.PhotoImage(image)

    # Calculate center coordinates
    x = (canvas.winfo_width() - tk_image.width()) // 2
    y = (canvas.winfo_height() - tk_image.height()) // 2

    canvas.create_image(x, y, anchor=tk.NW, image=tk_image)
    canvas.image = tk_image


def update_image():
    """
    Update the displayed image with a new random image and schedule the next update.
    """
    random_image_url = get_random_image_url()
    image = download_image(random_image_url)
    display_image(canvas, image)
    root.after(5000, update_image)  # Schedule the next update after 5000 ms (5 seconds)


root = tk.Tk()

label_frame = tk.LabelFrame(root, text="Image preview")
label_frame.pack(padx=10, pady=10, expand=True, fill=tk.BOTH)

canvas = tk.Canvas(label_frame, bg='black', height=200)
canvas.pack(expand=True, fill=tk.X)

root.update_idletasks()  # Update geometry information before the initial update
update_image()  # Initial update

root.mainloop()
