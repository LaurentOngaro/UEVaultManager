class GUISettings:
    # todo: integrate these settings into the UEVM config file
    def __init__(self):
        self.debug_mode = False

        self.app_title = 'UEVM Gui'
        self.app_width = 1600
        self.app_height = 930
        self.app_monitor = 1
        self.csv_datetime_format = '%Y-%m-%d %H:%M:%S'
        self.data_filetypes = (('csv file', '*.csv'), ('tcsv file', '*.tcsv'), ('json file', '*.json'), ('text file', '*.txt'))

        self.app_icon_filename = '../../assets/main.ico'
        self.csv_filename = '../../../results/list.csv'

        self.cache_folder = "../cache"
        self.cache_max_time = 60 * 60 * 24 * 15  # 15 days

        self.default_image_filename = './assets/UEVM_200x200.png'
        self.preview_max_width = 150
        self.preview_max_height = 150

        self.default_search_text = 'Text to search...'
        self.default_category_for_all = 'All'

        self.table_font_size = 10
        self.expand_columns_factor = 20
        self.contract_columns_factor = 20
