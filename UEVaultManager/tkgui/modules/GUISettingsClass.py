# coding=utf-8
"""
Implementation for:
- GUISettings: class containing all the settings for the GUI
"""


class GUISettings:
    """
    This class contains all the settings for the GUI.
    """

    def __init__(self):
        self.debug_mode = False

        self.app_title = 'UEVM Gui'
        self.app_width = 1600
        self.app_height = 935
        self.app_monitor = 1
        self.csv_datetime_format = '%Y-%m-%d %H:%M:%S'
        self.data_filetypes = (('csv file', '*.csv'), ('tcsv file', '*.tcsv'), ('json file', '*.json'), ('text file', '*.txt'))

        self.assets_folder = '../../assets'  # must be used trought gui_f.path_from_relative_to_absolute
        self.app_icon_filename = '../../assets/main.ico'  # must be used trought gui_f.path_from_relative_to_absolute
        self.csv_filename = '../../../results/list.csv'

        self.cache_folder = "../cache"
        self.cache_max_time = 60 * 60 * 24 * 15  # 15 days

        self.default_image_filename = './assets/UEVM_200x200.png'  # must be used trought gui_f.path_from_relative_to_absolute
        self.preview_max_width = 150
        self.preview_max_height = 150

        self.default_global_search = 'Text to search...'
        self.default_category_for_all = 'All'

        self.expand_columns_factor = 20
        self.contract_columns_factor = 20

        self.empty_cell = 'nan'
        # ttkbootstrap themes:
        # light themes : "cosmo", "flatly", "litera", "minty", "lumen", "sandstone", "yeti", "pulse", "united", "morph", "journal", "simplex", "cerculean"
        # dark themes: "darkly", "superhero", "solar", "cyborg", "vapor"
        self.theme_name = 'lumen'
        self.theme_font = ('Verdana', 8)

        self.datatable_default_pref = {
            'align': 'w',  #
            'cellbackgr': '#F4F4F3',  #
            'cellwidth': 100,  #
            'floatprecision': 2,  #
            'thousandseparator': '',  #
            'font': 'Verdana',  #
            'fontsize': 8,  #
            'fontstyle': '',  #
            'grid_color': '#ABB1AD',  #
            'linewidth': 1,  #
            'rowheight': 22,  #
            'rowselectedcolor': '#E4DED4',  #
            'textcolor': 'black'  #
        }
