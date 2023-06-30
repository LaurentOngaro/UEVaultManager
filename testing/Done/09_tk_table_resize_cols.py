import tkinter as tk
import pandas as pd
from pandastable import Table

expand_columns_factor = 20
contract_columns_factor = 20


# Load data from a CSV file into a pandas DataFrame
def load_csv_data(file_path):
    df = pd.read_csv(file_path)
    return df


# Function to expand the columns of the DataTable
def print_column_widths():
    for col_name, width in table.columnwidths.items():
        print(f"{col_name}: {width}")


def expand_columns():
    table.expandColumns(factor=expand_columns_factor)


def contract_columns():
    table.contractColumns(factor=contract_columns_factor)


def autofit_columns():
    table.autoResizeColumns()


def zoom_in():
    table.zoomIn()


def zoom_out():
    table.zoomOut()


# Create a Tkinter window and display the DataFrame in a Table
def display_dataframe_in_tkinter_table(df):
    # Create a Tkinter object
    root = tk.Tk()

    # Create a frame to hold the table
    frame = tk.Frame(root)
    frame.pack(fill='both', expand=True)

    # Add a title to the window
    root.title("CSV Data in a Tkinter Window")

    # Create and display the Table with the data from the DataFrame
    global table
    table = Table(frame, dataframe=df, showtoolbar=True, showstatusbar=True)
    table.show()

    table.fontsize = 10
    table.setFont()

    # Create a frame to hold the button
    button_frame = tk.Frame(root)
    button_frame.pack(fill='x', side='bottom')

    # Create a button to expand the columns and add it to the frame
    btn_print = tk.Button(button_frame, text="Print Width", command=print_column_widths)
    btn_print.pack(side='left')

    btn_autofit = tk.Button(button_frame, text="autofit", command=autofit_columns)
    btn_autofit.pack(side='left')

    btn_zoom_in = tk.Button(button_frame, text="zoom_in", command=zoom_in)
    btn_zoom_in.pack(side='left')

    btn_zoom_out = tk.Button(button_frame, text="zoom_out", command=zoom_out)
    btn_zoom_out.pack(side='left')

    btn_expand = tk.Button(button_frame, text="expand", command=expand_columns)
    btn_expand.pack(side='left')

    btn_contract = tk.Button(button_frame, text="contract", command=contract_columns)
    btn_contract.pack(side='left')

    # Start the main Tkinter loop
    root.mainloop()


if __name__ == "__main__":
    # Replace 'file_path' with the path to your CSV file
    file_path = 'K:/UE/UEVM/Results//list.csv'
    df = load_csv_data(file_path)
    display_dataframe_in_tkinter_table(df)
