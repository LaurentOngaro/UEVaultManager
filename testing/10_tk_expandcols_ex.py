import tkinter as tk
from tkinter import ttk


def main():
    # Create a Tkinter object
    root = tk.Tk()

    # Add a title to the window
    root.title("Tkinter Layout with Header and 1 Row and 3 Columns")

    grid_def_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'sticky': tk.NSEW}

    # Create a frame for the header
    header_frame = ttk.Frame(root)
    header_frame.pack(fill='x')

    # Create a label for the header
    header_label = ttk.Label(header_frame, text="Header", font=("Arial", 16))
    header_label.pack(pady=10)

    # Create a frame to hold the elements with columns
    columns_frame = ttk.Frame(root)
    columns_frame.pack(fill='both', expand=True)

    # Create three LabelFrames to place in each column
    label_frame1 = ttk.LabelFrame(columns_frame, text="Column 1")
    label_frame2 = ttk.LabelFrame(columns_frame, text="Column 2")
    label_frame3 = ttk.LabelFrame(columns_frame, text="Column 3")

    # Place the LabelFrames in the grid using the grid() geometry manager
    label_frame1.grid(row=0, column=0, **grid_def_options)
    label_frame2.grid(row=0, column=1, **grid_def_options)
    label_frame3.grid(row=0, column=2, **grid_def_options)

    # Create two buttons for the first and third LabelFrames
    button1_1 = ttk.Button(label_frame1, text="Button 1-1")
    button1_2 = ttk.Button(label_frame1, text="Button 1-2")
    button3_1 = ttk.Button(label_frame3, text="Button 3-1")
    button3_2 = ttk.Button(label_frame3, text="Button 3-2")

    # Create a canvas for the second LabelFrame
    canvas = tk.Canvas(label_frame2, bg="white", width=150, height=150)

    # Place the buttons in the first and third LabelFrames using the grid() geometry manager
    button1_1.grid(row=0, column=0, **grid_def_options)
    button1_2.grid(row=0, column=1, **grid_def_options)
    button3_1.grid(row=0, column=0, **grid_def_options)
    button3_2.grid(row=0, column=1, **grid_def_options)

    # Place the canvas in the second LabelFrame using the grid() geometry manager
    canvas.grid(row=0, column=0, columnspan=2, padx=5, pady=5)

    # Configure the columns to take all the available width
    columns_frame.columnconfigure(0, weight=1)
    columns_frame.columnconfigure(1, weight=1)
    columns_frame.columnconfigure(2, weight=1)

    # Start the main Tkinter loop
    root.mainloop()


if __name__ == "__main__":
    main()
