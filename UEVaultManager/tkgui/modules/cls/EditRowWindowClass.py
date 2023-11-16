# coding=utf-8
"""
Implementation for:
- EditRowWindow: window to edit a row.
"""
import tkinter as tk
from tkinter import ttk

from ttkbootstrap import INFO, WARNING

import UEVaultManager.tkgui.modules.functions as gui_f  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.functions_no_deps as gui_fn  # using the shortest variable name for globals for convenience
import UEVaultManager.tkgui.modules.globals as gui_g  # using the shortest variable name for globals for convenience
from UEVaultManager.tkgui.modules.cls.ImagePreviewWindowClass import ImagePreviewWindow
from UEVaultManager.tkgui.modules.types import DataFrameUsed


class EditRowWindow(tk.Toplevel):
    """
    The window to edit a row.
    :param parent: parent window.
    :param title: title of the window.
    :param width: width of the window.
    :param height: height of the window.
    :param icon: icon of the window.
    :param screen_index: index of the screen on which the window will be displayed.
    :param editable_table: table to edit.
    """

    def __init__(self, parent, title: str, width: int = 600, height: int = 800, icon=None, screen_index: int = 0, editable_table=None):
        super().__init__(parent)
        self.title(title)
        try:
            # an error can occur here AFTER a tool window has been opened and closed (ex: db "import/export")
            self.style = gui_fn.set_custom_style(gui_g.s.theme_name, gui_g.s.theme_font)
        except Exception as error:
            gui_f.log_warning(f'Error in EditRowWindow: {error!r}')
        self.geometry(gui_fn.center_window_on_screen(screen_index, width, height))
        gui_fn.set_icon_and_minmax(self, icon)
        self.screen_index = screen_index
        self.resizable(True, False)

        self.editable_table = editable_table
        self.preview_scale = 0.25
        self.must_save: bool = False
        self.initial_values = []
        self.width: int = width
        # the photoimage is stored is the variable to avoid garbage collection
        # see: https://stackoverflow.com/questions/30210618/image-not-getting-displayed-on-tkinter-through-label-widget
        self.canvas_image = None
        self.image_url: str = ''
        self.frm_control = self.ControlFrame(self)
        self.frm_content = self.ContentFrame(self)

        self.frm_control.pack(ipadx=5, ipady=5, fill=tk.X)
        self.frm_content.pack(ipadx=5, ipady=5, padx=5, pady=5, fill=tk.X)

        self.bind('<Tab>', self._focus_next_widget)
        self.bind('<Control-Tab>', self._focus_next_widget)
        self.bind('<Shift-Tab>', self._focus_prev_widget)
        self.bind('<Key>', self.on_key_press)
        self.bind('<Button-1>', self.on_left_click)
        self.protocol('WM_DELETE_WINDOW', self.on_close)

        gui_g.WindowsRef.edit_row = self
        # gui_f.make_modal(self)  # could cause issue if done in the init of the class. better to be done by the caller
        self.after(500, self.update_controls_state)  # run after a delay to let the caller fill the widgets

    @staticmethod
    def _focus_next_widget(event):
        event.widget.tk_focusNext().focus()
        return 'break'

    @staticmethod
    def _focus_prev_widget(event):
        event.widget.tk_focusPrev().focus()
        return 'break'

    class ContentFrame(ttk.Frame):
        """
        The frame containing the editable fields.
        :param container: parent window.
        """

        def __init__(self, container):
            super().__init__(container)

    class ControlFrame(ttk.Frame):
        """
        The frame containing the buttons.
        :param container: parent window.
        """

        def __init__(self, container):
            super().__init__(container)
            pack_def_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'fill': tk.X, 'anchor': tk.NW}
            grid_def_options = {'ipadx': 0, 'ipady': 0, 'padx': 2, 'pady': 2, 'sticky': tk.NSEW}

            width = int(gui_g.s.preview_max_width * container.preview_scale)
            height = int(gui_g.s.preview_max_height * container.preview_scale)
            lbf_preview = ttk.LabelFrame(self, text='Clic to Zoom')
            lbf_preview.grid(row=0, column=0, **grid_def_options)
            canvas_image = tk.Canvas(lbf_preview, width=width, height=height)
            canvas_image.pack(**pack_def_options)
            # add a bind on left clic on the image to display it in a ImagePreviewWindow
            canvas_image.bind('<Button-1>', container.open_image_preview)

            lblf_actions = ttk.LabelFrame(self, text='Actions')
            lblf_actions.grid(row=0, column=1, **grid_def_options)

            btn_prev_asset_edit = ttk.Button(lblf_actions, text='Prev Asset', command=container.prev_asset)
            btn_prev_asset_edit.pack(**pack_def_options, side=tk.LEFT)
            btn_next_asset_edit = ttk.Button(lblf_actions, text='Next Asset', command=container.next_asset)
            btn_next_asset_edit.pack(**pack_def_options, side=tk.LEFT)
            self.btn_open_json = ttk.Button(lblf_actions, text='Open Json', command=container.open_json_file)
            self.btn_open_json.pack(**pack_def_options, side=tk.LEFT)
            btn_open_url = ttk.Button(lblf_actions, text='Open URL', command=container.open_asset_url)
            btn_open_url.pack(**pack_def_options, side=tk.LEFT)
            btn_open_folder = ttk.Button(lblf_actions, text='Open Folder', command=container.open_asset_folder)
            btn_open_folder.pack(**pack_def_options, side=tk.LEFT)
            # noinspection PyArgumentList
            # (bootstyle is not recognized by PyCharm)
            ttk_item = ttk.Button(lblf_actions, text='Close', command=container.on_close, bootstyle=WARNING)
            ttk_item.pack(**pack_def_options, side=tk.RIGHT)
            # noinspection PyArgumentList
            # (bootstyle is not recognized by PyCharm)
            btn_save_row = ttk.Button(lblf_actions, text='Save Changes', command=container.save_changes, bootstyle=INFO)
            btn_save_row.pack(**pack_def_options, side=tk.RIGHT)

            self.columnconfigure(0, weight=1)
            self.columnconfigure(1, weight=2)
            self.columnconfigure(2, weight=1)

            self.canvas_image = canvas_image

            widget_list = gui_g.stated_widgets.get('not_first_asset', [])
            gui_fn.append_no_duplicate(widget_list, [btn_prev_asset_edit])
            widget_list = gui_g.stated_widgets.get('not_last_asset', [])
            gui_fn.append_no_duplicate(widget_list, [btn_next_asset_edit])
            widget_list = gui_g.stated_widgets.get('table_has_changed', [])
            gui_fn.append_no_duplicate(widget_list, btn_save_row)
            widget_list = gui_g.stated_widgets.get('asset_has_url', [])
            gui_fn.append_no_duplicate(widget_list, [btn_open_url])
            widget_list = gui_g.stated_widgets.get('asset_added_mannually', [])
            gui_fn.append_no_duplicate(widget_list, [btn_open_folder])

    def on_close(self, _event=None) -> None:
        """
        Event when the window is closing.
        :param _event: event that triggered the call of this function.
        """
        if self.must_save:
            if gui_f.box_yesno('Changes have been made in the window. Do you want to keep them ?'):
                self.save_changes()
        self.close_window()

    # noinspection DuplicatedCode
    def on_key_press(self, event):
        """
        Event when a key is pressed.
        :param event: event that triggered the call of this function.
        """
        self.update_controls_state()
        control_pressed = event.state == 4 or event.state & 0x00004 != 0
        if event.keysym == 'Escape':
            self.on_close()
        elif control_pressed and (event.keysym == 's' or event.keysym == 'S'):
            self.save_changes()
        return 'break'

    # noinspection PyUnusedLocal
    def on_left_click(self, event=None) -> None:
        """
        When the left mouse button is clicked, show the selected row in the quick edit frame.
        :param event: event that triggered the call of this function.
        """
        self.update_controls_state()  # to update when clicking on the checkbox

    def close_window(self) -> None:
        """
        Close the window.
        """
        gui_g.WindowsRef.edit_row = None
        self.editable_table.reset_style()
        self.destroy()

    def save_changes(self) -> None:
        """
        Save the changes (Wrapper).
        """
        self.must_save = False
        self.editable_table.save_edit_row()

    def prev_asset(self) -> None:
        """
        Go to the previous asset (Wrapper).
        """
        self.close_image_preview()
        row_number = self.editable_table.prev_row()
        self.editable_table.edit_row(row_number)

    def next_asset(self) -> None:
        """
        Go to the next asset (Wrapper).
        """
        self.close_image_preview()
        row_number = self.editable_table.next_row()
        self.editable_table.edit_row(row_number)

    def open_asset_url(self) -> None:
        """
        Open the asset URL (Wrapper).
        """
        self.close_image_preview()
        self.editable_table.open_asset_url()

    def open_asset_folder(self) -> None:
        """
        Open the asset URL (Wrapper).
        """
        self.close_image_preview()
        self.editable_table.open_origin_folder()

    def open_json_file(self) -> None:
        """
        Open the source file of the asset (Wrapper).
        """
        self.close_image_preview()
        self.editable_table.open_json_file()

    def update_controls_state(self) -> None:
        """
        Update some controls in the window depending on conditions
        """
        data_table = self.editable_table  # shortcut
        max_index = len(data_table.get_data(df_type=DataFrameUsed.AUTO))
        current_index = data_table.add_page_offset(data_table.getSelectedRow())
        gui_f.update_widgets_in_list(current_index > 0, 'not_first_asset')
        gui_f.update_widgets_in_list(current_index < max_index - 1, 'not_last_asset')

        current_values = self.editable_table.get_edited_row_values()
        self.must_save = current_values and self.initial_values != current_values
        gui_f.update_widgets_in_list(self.must_save, 'table_has_changed')

        # conditions based on info about the current asset
        widgets = data_table.get_edited_row_values()
        if len(widgets):
            is_added = widgets.get('Added manually', False)
            is_marketplace = widgets.get('Origin', '') == gui_g.s.origin_marketplace
            url = widgets.get('Url', '')
            gui_f.update_widgets_in_list(is_added, 'asset_added_mannually')
            gui_f.update_widgets_in_list(url != '', 'asset_has_url')
            gui_f.set_widget_state(self.frm_control.btn_open_json, is_marketplace)

    def update_image_preview(self) -> bool:
        """
        Update the image preview.
        :return: True if the image was displayed, False otherwise.
        """
        url = self.image_url
        if not gui_f.show_asset_image(image_url=url, canvas_image=self.frm_control.canvas_image, scale=self.preview_scale):
            return False
        self.update_controls_state()
        return True

    def open_image_preview(self, _event):
        """
        Open the image preview window.
        """
        widgets = self.editable_table.get_edited_row_values()
        url = widgets.get('Image', '')
        if gui_g.WindowsRef.image_preview:
            gui_g.WindowsRef.image_preview.close_window()
        ipw = ImagePreviewWindow(
            title='Image Preview', screen_index=self.screen_index, url=url, width=gui_g.s.preview_max_width, height=gui_g.s.preview_max_height
        )
        if not ipw.display(url=url):
            ipw.close_window()
        else:
            gui_f.make_modal(ipw)  # make the preview window modal
        gui_f.make_modal(self)  # (re)make the edit row window modal

    @staticmethod
    def close_image_preview():
        """
        Close the image preview window.
        """
        if gui_g.WindowsRef.image_preview:
            gui_g.WindowsRef.image_preview.close_window()
