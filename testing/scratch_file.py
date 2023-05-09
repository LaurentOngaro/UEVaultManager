import tkinter as tk
import requests
from PIL import Image, ImageTk
import io
import random


# generate a random number between 100 and 200
def get_random_number():
    return random.randint(100, 200)


def get_random_image_url():
    # Replace this function with the logic to generate a random image URL from a website
    return f'https://picsum.photos/{get_random_number()}'


def download_image(url):
    response = requests.get(url)
    image_data = response.content
    image = Image.open(io.BytesIO(image_data))
    return image


def display_image(canvas, image):
    tk_image = ImageTk.PhotoImage(image)

    # Calculate center coordinates
    x = (canvas.winfo_width() - tk_image.width()) // 2
    y = (canvas.winfo_height() - tk_image.height()) // 2

    canvas.create_image(x, y, anchor=tk.NW, image=tk_image)
    canvas.image = tk_image


def update_image():
    random_image_url = get_random_image_url()
    image = download_image(random_image_url)
    display_image(canvas, image)
    root.after(5000, update_image)  # Schedule the next update after 10000 ms (10 seconds)


root = tk.Tk()

label_frame = tk.LabelFrame(root, text="Image preview")
label_frame.pack(padx=10, pady=10, expand=True, fill=tk.BOTH)

canvas = tk.Canvas(label_frame, bg='black', height=200)
canvas.pack(expand=True, fill=tk.X)

root.update_idletasks()  # Update geometry information before the initial update
update_image()  # Initial update

root.mainloop()
