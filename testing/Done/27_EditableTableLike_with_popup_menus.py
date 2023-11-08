import tkinter as tk
import pandas as pd
import sqlite3
from pandastable import applyStyle, Table

db_file_name = 'K:/UE/UEVM/scraping/assets.db'


def columns_to_CSV_heading(word: str) -> str:
    """ Convert column names to CamelCase """
    heading = ' '.join(x for x in word.split('_'))
    heading = heading.capitalize()
    return heading


class EditableTable(Table):

    def __init__(self, container, db_name: str = '', **kwargs) -> None:
        self.container = container
        self.df: pd.DataFrame = self.load_data_from_db(db_name)
        Table.__init__(self, parent=container, dataframe=self.df,  #
                       showtoolbar=False,  #
                       showstatusbar=False,  #
                       # enable_menus=False,
                       **kwargs)

    @staticmethod
    def load_data_from_db(db_name: str) -> pd.DataFrame:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM assets")

        rows = cursor.fetchall()
        column_names = [description[0] for description in cursor.description]

        df = pd.DataFrame(rows, columns=column_names)

        cursor.close()
        conn.close()

        # Convert column names to CamelCase
        df.columns = [columns_to_CSV_heading(col) for col in df.columns]

        return df

    def show(self, callback=None):
        """
        Overwrite the default show method
        """
        super().show()
        # overwriting the popupMenu method for col and row headers.
        # Must be done AFTER table.show() because they are created in that method
        self.colheader.popupMenu = self.colheader_popup_menu
        self.rowheader.popupMenu = self.rowheader_popup_menu

    def popupMenu(self, event, rows=None, cols=None, outside=None):
        """Add left and right click behaviour for canvas, should not have to override
            this function, it will take its values from defined dicts in constructor"""

        def _popup_focus_out(_event):
            popupmenu.unpost()

        def _create_sub_menu(parent, label, commands):
            menu = tk.Menu(parent, tearoff=0)
            popupmenu.add_cascade(label=label, menu=menu)
            for _action in commands:
                menu.add_command(label=_action, command=defaultactions[_action])
            applyStyle(menu)
            return menu

        def _add_commands(fieldtype):
            functions = self.columnactions[fieldtype]
            for f in list(functions.keys()):
                func = getattr(self, functions[f])
                popupmenu.add_command(label=f, command=lambda: func(row, col))
            return

        def _add_defaultcommands():
            """now add general actions for all cells"""
            for _action in cmd_inside_no_submenu:
                if _action == 'Fill Down' and (rows is None or len(rows) <= 1):
                    continue
                if _action == 'Undo' and self.prevdf is None:
                    continue
                else:
                    popupmenu.add_command(label=_action, command=defaultactions[_action])
            return

        defaultactions = {
            # edit
            'Copy': lambda: self.copy(rows, cols),
            'Undo': self.undo,
            'Paste': self.paste,
            'Undo Last Change': self.undo,
            # table
            # 'Fill Down': lambda: self.fillDown(rows, cols),
            # 'Table to Text': self.showasText,
            # 'Clean Data': self.cleanData,
            'Clear Formatting': self.clearFormatting,
            'Clear Data': lambda: self.deleteCells(rows, cols),
            'Select All': self.selectAll,
            'Table Info': self.showInfo,
            # 'Show as Text': self.showasText,
            'Filter Rows': self.queryBar,
            'Preferences': self.showPreferences,
            # 'Copy Table': self.copyTable,
            'Find/Replace': self.findText,
            # 'Sort by index': lambda: self.table.sortTable(index=True),
            # 'Reset index': self.table.resetIndex,
            'Color by Value': self.setColorbyValue,
            # rows
            'Add Row(s)': self.addRows,
            # row(s) selected
            'Delete Row(s)': lambda: self.deleteRow(ask=True),
            'Copy Row(s)': self.duplicateRows,
            # BUGGY with editabletable 'Set Row Color': self.setRowColors,
            # columns
            'Add Column(s)': self.addColumn,
            # columns(s) selected
            'Delete Column(s)': lambda: self.deleteColumn(ask=True),
            'Copy column': self.copyColumn,
            'Align column': self.setAlignment,
            'Sort columns by row': self.sortColumnIndex,
            'Move column to Start': self.moveColumns,
            'Move column to End': lambda: self.moveColumns(pos='end'),
            'Set column Color': self.setColumnColors,
            # BUGGY with editabletable 'Value Counts': self.valueCounts,
            'String Operation': self.applyStringMethod,
            'Set Data Type': self.setColumnType,
            # files
            # 'New': self.new,
            # 'Open': self.load,
            # 'Save': self.save,
            # 'Save As': self.saveAs,
            # 'Import Text/CSV': lambda: self.importCSV(dialog=True),
            # 'Import hdf5': lambda: self.importHDF(dialog=True),
            # 'Export': self.doExport,
            # ploting
            # 'Plot Selected': self.plotSelected,
            # 'Hide plot': self.hidePlot,
            # 'Show plot': self.showPlot,

            # custom actions
            'Add to Sticky Rows': self.add_to_sticky_rows,
            'Remove from Sticky Rows': self.remove_from_sticky_rows
        }
        popupmenu = tk.Menu(self, tearoff=0)

        row = self.get_row_clicked(event)
        col = self.get_col_clicked(event)
        multicols = self.multiplecollist
        colnames = list(self.df.columns[multicols])[:4]
        colnames = [str(i)[:20] for i in colnames]
        if len(colnames) > 2:
            colnames = ','.join(colnames[:2]) + '+%s others' % str(len(colnames) - 2)
        else:
            colnames = ','.join(colnames)

        cmd_inside_no_submenu = ['Add to Sticky Rows', 'Remove from Sticky Rows']
        cmd_inside_edit = ['Copy', 'Paste', 'Undo', 'Undo Last Change']
        cmd_both_no_submenu = []
        cmd_both_table = [
            'Select All', 'Filter Rows', 'Find/Replace', 'Clear Data', 'Clear Formatting', 'Color by Value', 'Preferences', 'Table Info'
        ]
        cmd_row_selected = ['Delete Row(s)', 'Copy Row(s)']
        cmd_col_selected = [
            'Delete Column(s)', 'Copy column', 'Align column', 'Sort columns by row', 'Move column to Start', 'Move column to End',
            'Set column Color', 'Value Counts', 'String Operation', 'Set Data Type',
        ]
        cmd_header_cols = ['Add Column(s)']
        cmd_header_rows = ['Add Row(s)']

        if outside is None:
            # On the data
            _add_defaultcommands()
            popupmenu.add_separator()
            _create_sub_menu(popupmenu, 'Edit', cmd_inside_edit)
            if col:
                coltype = self.model.getColumnType(col)
                if coltype in self.columnactions:
                    _add_commands(coltype)
                popupmenu.add_separator()
                _create_sub_menu(popupmenu, 'Columns', cmd_col_selected)
            if row:
                popupmenu.add_separator()
                _create_sub_menu(popupmenu, 'Rows', cmd_row_selected)
        else:
            # Outside the data (i.e. on a header)
            # TODO: add a check if it's a column header or a row header
            # if it's a column header, show specific items
            col_menu = _create_sub_menu(popupmenu, 'Columns', cmd_header_cols)
            col_menu.add_command(label='Sort by ' + colnames + ' \u2193', command=lambda: self.sortTable(ascending=[1 for i in multicols]))
            col_menu.add_command(label='Sort by ' + colnames + ' \u2191', command=lambda: self.sortTable(ascending=[0 for i in multicols]))
            # if it's a row header, show specific items
            _create_sub_menu(popupmenu, 'Rows', cmd_header_rows)

        for action in cmd_both_no_submenu:
            popupmenu.add_command(label=action, command=defaultactions[action])

        popupmenu.add_separator()
        _create_sub_menu(popupmenu, 'Table', cmd_both_table)

        popupmenu.bind('<FocusOut>', _popup_focus_out)
        popupmenu.focus_set()
        popupmenu.post(event.x_root, event.y_root)
        applyStyle(popupmenu)
        return popupmenu

    def colheader_popup_menu(self, event, outside=True):
        """Overwrite the default colheader popupMenu method"""
        print('colheader_popupMenu')
        return self.popupMenu(event, outside=outside)

    def rowheader_popup_menu(self, event, outside=True):
        """Overwrite the default rowheader popupMenu method"""
        print('rowheader_popupMenu')
        return self.popupMenu(event, outside=outside)

    def add_to_sticky_rows(self):
        """ Add selected rows to sticky rows"""
        print('add_to_sticky_rows')

    def remove_from_sticky_rows(self):
        """ Remove selected rows from sticky rows"""
        print('remove_from_sticky_rows')


main = tk.Tk()
main.title('MAIN Window')
main.geometry('1200x1000+2700+50')
frm = tk.Frame(main)
frm.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
# btn_close = tk.Button(main, text='Close', command=main.destroy)
# btn_close.pack(side=tk.LEFT, pady=10)

table = EditableTable(frm, db_file_name)
table.show()
main.mainloop()
