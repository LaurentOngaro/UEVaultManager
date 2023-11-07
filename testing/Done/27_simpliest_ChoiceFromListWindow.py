import tkinter as tk
from UEVaultManager.tkgui.modules.cls.ChoiceFromListWindowClass import ChoiceFromListWindow

result = None
json_data = {
    'csv': {
        'value': 'csv',
        'desc': 'All the columns data of the selected rows will be exported in a CSV file (comma separated values)'
    },
    'list': {
        'value': 'list',
        'desc': 'Only the "Asset id" column of the selected rows will be exported in a text file (one value by line)'
    },
    'filter': {
        'value': 'filter',
        'desc': 'The "Asset id" column will be exported as a ready to use filter in a json file '
    },
}


def get_result(selection):
    """
    Set the chosen value.
    """
    global result
    result = selection


if __name__ == '__main__':
    main = tk.Tk()
    main.title('FAKE MAIN Window')
    main.geometry('200x100')
    ChoiceFromListWindow(
        window_title='Choose the export format',
        width=220,
        height=250,
        json_data=json_data,
        show_validate_button=True,
        first_list_width=13,
        get_result_func=get_result,
        is_modal=True,
    )
    print(f'The value {result} has been SELECTED')
    # main.mainloop()
