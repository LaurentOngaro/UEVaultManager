import tkinter as tk
import ttkbootstrap as ttk


class WindowClass(tk.Tk):

    def __init__(self):
        super().__init__()
        self.style = ttk.Style('lumen')

        self.geometry("400x500")
        self.content_frame = self.ContentFrame(self)
        self.control_frame = self.ControlFrame(self)

        self.content_frame.pack(ipadx=5, ipady=5, padx=5, pady=5, fill=tk.X)
        self.control_frame.pack(ipadx=5, ipady=5, padx=5, pady=5, fill=tk.X)

    class ContentFrame(ttk.Frame):

        def __init__(self, container):
            super().__init__(container)
            # create a Text widget with some dummy text and add it to the main frame
            dummy_text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Pellentesque ultrices scelerisque libero non pellentesque. Proin bibendum sapien eu sapien gravida, vel bibendum magna tempor. Aliquam semper cursus dui\n"
            for i in range(10):
                dummy_text += dummy_text
            self.text_content = tk.Text(self)
            self.text_content.insert("end", dummy_text)

            # create a Scrollbar and associate it with the Text widget
            scrollbar = ttk.Scrollbar(self)
            scrollbar.pack(side="right", fill="y")
            scrollbar.config(command=self.text_content.yview)
            self.text_content.config(yscrollcommand=scrollbar.set)
            self.text_content.pack(side="left", fill="both", expand=True)

    class ControlFrame(ttk.Frame):

        def __init__(self, container):
            super().__init__(container)
            pack_def_options = {'ipadx': 2, 'ipady': 2, 'padx': 2, 'pady': 2, 'fill': tk.BOTH, 'expand': False}
            lblf_def_options = {'ipadx': 1, 'ipady': 1, 'expand': True, 'fill': tk.X}
            lblf_commands = ttk.LabelFrame(self, text='Commands')
            lblf_commands.pack(**lblf_def_options)
            button1 = ttk.Button(lblf_commands, text="Button 1")
            button1.pack(**pack_def_options, side=tk.LEFT)
            button2 = ttk.Button(lblf_commands, text="Button 2")
            button2.pack(**pack_def_options, side=tk.LEFT)


if __name__ == "__main__":
    app = WindowClass()
    app.mainloop()
