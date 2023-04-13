import tkinter as tk
from tkinter import ttk
from pandastable import Table
import pandas as pd


def update_table():
    global total_pages
    filters = [entry.get() for entry in entries]
    mask = df.apply(lambda row: all([True if f == '' else f in str(row[i]) for i, f in enumerate(filters)]), axis=1)
    filtered_df = df[mask]
    total_pages = (len(filtered_df) - 1) // rows_per_page + 1
    start = (current_page-1) * rows_per_page
    end = start + rows_per_page
    table.model.df = filtered_df.iloc[start:end]
    table.redraw()
    total_results_label.config(text=f"Total Results: {len(filtered_df)}")
    total_pages_label.config(text=f"Total Pages: {total_pages}")
    current_page_label.config(text=f"Current Page: {current_page}")


def next_page():
    global current_page
    if current_page < total_pages:
        current_page += 1
        update_table()


def prev_page():
    global current_page
    if current_page > 1:
        current_page -= 1
        update_table()


df = pd.read_csv('../results/list.csv')

root = tk.Tk()

filter_frame = tk.Frame(root)
filter_frame.pack(fill=tk.X, expand=True)
entries = []
for i, col in enumerate(df.columns):
    label = ttk.Label(filter_frame, text=col)
    label.grid(row=0, column=i)
    entry = tk.Entry(filter_frame)
    entry.grid(row=1, column=i)
    entry.bind('<KeyRelease>', lambda event: update_table())
    entries.append(entry)


rows_per_page = 10
total_pages = (len(df) - 1) // rows_per_page + 1
current_page = 1
data_frame = tk.Frame(root)
data_frame.pack(fill=tk.X, expand=True)
table = Table(data_frame, dataframe=df.iloc[0:rows_per_page])
table.show()


info_frame = tk.Frame(root)
info_frame.pack(fill=tk.X, expand=True)

total_results_label = ttk.Label(info_frame, text=f"Total Results: {len(df)}")
total_results_label.pack(side=tk.LEFT)

total_pages_label = ttk.Label(info_frame, text=f"Total Pages: {total_pages}")
total_pages_label.pack(side=tk.LEFT)

current_page_label = ttk.Label(info_frame, text=f"Current Page: {current_page}")
current_page_label.pack(side=tk.LEFT)

navigation_frame = tk.Frame(root)
navigation_frame.pack(fill=tk.X, expand=True)

prev_button = tk.Button(navigation_frame, text="Prev", command=prev_page)
prev_button.pack(side=tk.LEFT)

next_button = tk.Button(navigation_frame, text="Next", command=next_page)
next_button.pack(side="right")

root.mainloop()
