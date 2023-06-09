# coding=utf-8
"""
implementation for:
- VersionNum: The version of the database or/and class.
- DatabaseConnection: Context manager for opening and closing a database connection.
- UEAssetDbHandler: Handles database operations for the UE Assets.
"""
import datetime
import inspect
import logging
import os
import random
import sqlite3
from enum import Enum

from faker import Faker

from UEVaultManager.tkgui.modules.functions_no_deps import path_from_relative_to_absolute
from UEVaultManager.utils.cli import init_dict_from_data, check_and_create_path


class VersionNum(Enum):
    """
    The version of the database or/and class.
    Used when checking if database must be upgraded by comparing with the class version
    """
    # when a new version is added to the VersionNum enum
    # - add code for the new version to the create_tables() method
    # - add code for the new version check to the check_and_upgrade_database() method
    V0 = 0  # invalid version
    V1 = 1  # initial version : only the "standard" marketplace columns
    V2 = 2  # add the columns used fo user data to the "standard" marketplace columns
    V3 = 3  # add the last_run table to get data about the last run of the app


class DatabaseConnection:
    """
    Context manager for opening and closing a database connection
    :param ldb_name: The name of the database file.
    """

    def __init__(self, ldb_name: str):
        self.db_name = ldb_name

    def __enter__(self):
        """
        Open the database connection.
        :return: The sqlite3.Connection object.
        """
        self.conn = sqlite3.connect(self.db_name)
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Close the database connection.
        :param exc_type: Exception type.
        :param exc_val: Exception value.
        :param exc_tb: Exception traceback.
        """
        self.conn.close()


class UEAssetDbHandler:
    """
    Handles database operations for the UE Assets.
    Note: The database will be created if it doesn't exist.
    :param ldb_name: The name of the database file.
    """

    def __init__(self, ldb_name: str):
        self.logger = logging.getLogger(__name__)
        # self.logger.setLevel(logging.DEBUG)
        self.db_name = ldb_name
        self.db_version = VersionNum.V0  # updated in check_and_upgrade_database()
        self.check_and_upgrade_database()

    def _get_db_version(self) -> VersionNum:
        """
        Check the database version.
        :return: The database version.
        """
        try:
            with DatabaseConnection(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('PRAGMA user_version')
                ret = int(cursor.fetchone()[0])  # type: int
                db_version = VersionNum(ret)
                return db_version
        except sqlite3.OperationalError:
            self.logger.critical('Could not get the database version')
            return VersionNum.V0

    def _set_db_version(self, new_version: VersionNum) -> None:
        """
        Set the database version.
        :param new_version: The new database version.
        """
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute(f'PRAGMA user_version = {new_version.value}')
            self.logger.info(f'database version is now set to {new_version}')

    def _check_db_version(self, minimal_db_version: VersionNum, caller_name='this method') -> bool:
        """
        Check if the database version is compatible with the current method.
        :param minimal_db_version: The minimal database version that is compatible with the current method.
        :param caller_name: The name of the method that called this method.
        :return:  True if the database version is compatible, otherwise False.
        """
        if self.db_version.value < minimal_db_version.value:
            message = f'This version of {caller_name} is only compatible with {minimal_db_version} or more database.\nPlease upgrade the database first.'
            self.logger.critical(message)
            return False
        return True

    def db_exists(self) -> bool:
        """
        Check if the database file exists.
        :return: True if the database file exists, otherwise False.
        """
        return os.path.exists(self.db_name)

    def create_tables(self, upgrade_to_version=VersionNum.V1) -> None:
        """
        Create the tables if they don't exist.
        :param upgrade_to_version: The database version we want to upgrade TO
        """
        # all the following steps must be run sequentially
        if upgrade_to_version.value >= VersionNum.V1.value:
            if not self.is_table_exist('assets'):
                with DatabaseConnection(self.db_name) as conn:
                    cursor = conn.cursor()
                    # create the first version of the database
                    # Notes:
                    # - this table has the same structure as the json files saved inside the method UEAssetScraper.save_to_file()
                    # - the order of columns must match the order of the fields in init_data() method
                    sql = """
                    CREATE TABLE IF NOT EXISTS assets ( 
                        id TEXT PRIMARY KEY, 
                        namespace TEXT, 
                        catalog_item_id TEXT, 
                        title TEXT, 
                        category TEXT, 
                        author TEXT, 
                        thumbnail_url TEXT, 
                        current_price_discounted REAL, 
                        asset_slug TEXT, 
                        currency_code TEXT, 
                        description TEXT, 
                        technical_details TEXT, 
                        long_description TEXT, 
                        categories TEXT, 
                        tags TEXT, 
                        comment_rating_id TEXT, 
                        rating_id TEXT, 
                        status TEXT, 
                        price REAL, 
                        discount REAL, 
                        discount_price REAL, 
                        discount_percentage REAL, 
                        is_featured BOOLEAN, 
                        is_catalog_item BOOLEAN, 
                        is_new BOOLEAN, 
                        free BOOLEAN, 
                        discounted BOOLEAN, 
                        can_purchase BOOLEAN, 
                        owned INTEGER, 
                        review REAL, 
                        review_count INTEGER
                    )
                    """
                    cursor.execute(sql)
                    conn.commit()
        if upgrade_to_version.value >= VersionNum.V3.value:
            if not self.is_table_exist('last_run'):
                # note : this table has the same structure as the data saved in the last_run_filename inside the method UEAssetScraper.save_all_to_files()
                with DatabaseConnection(self.db_name) as conn:
                    cursor = conn.cursor()
                    sql = "CREATE TABLE IF NOT EXISTS last_run (date DATETIME, files_count INTEGER, items_count INTEGER, items_ids TEXT)"
                    cursor.execute(sql)
                    conn.commit()

    def check_and_upgrade_database(self, upgrade_from_version: VersionNum = None) -> None:
        """
        Change the tables structure according to different versions.
        :param upgrade_from_version: The version we want to upgrade FROM. if None, the current version will be used
        """
        # force an update of the db_version property
        self.db_version = self._get_db_version()
        # if self.db_version == VersionNum.V0:
        #    raise Exception("Invalid database version or database is badly initialized")

        if upgrade_from_version is None:
            upgrade_from_version = self.db_version

        # all the following steps must be run sequentially
        if upgrade_from_version.value <= VersionNum.V1.value:
            # necessary steps to upgrade to version 1, aka create tables
            self.logger.info(f'Upgrading database from {upgrade_from_version}')
            self.create_tables(upgrade_to_version=VersionNum.V1)
            # necessary steps to upgrade to version 2
            with DatabaseConnection(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(assets)")
                columns = {row[1]: row for row in cursor.fetchall()}
                required_columns = {
                    'comment': 'TEXT',
                    'stars': 'INTEGER',
                    'must_buy': 'BOOL',
                    'test_result': 'TEXT',
                    'installed_folder': 'TEXT',
                    'alternative': 'TEXT',
                    'origin': 'TEXT'
                }
                for column_name, data_type in required_columns.items():
                    if column_name not in columns:
                        cursor.execute(f'ALTER TABLE assets ADD COLUMN {column_name} {data_type}')
                conn.commit()
                self.db_version = VersionNum.V2
                upgrade_from_version = self.db_version
                self.logger.info(f'Database upgraded to {upgrade_from_version}')
        if upgrade_from_version == VersionNum.V2:
            # necessary steps to upgrade to version 3
            self.create_tables(upgrade_to_version=VersionNum.V3)
            self.db_version = VersionNum.V3
            upgrade_from_version = self.db_version
            self.logger.info(f'Database upgraded to {upgrade_from_version}')
        if upgrade_from_version == VersionNum.V3:
            # necessary steps to upgrade to version 4
            # does not exist yet
            # do stuff here
            # self.db_version = VersionNum.V4
            # upgrade_from_version = self.db_version
            # self.logger.info(f'Database upgraded to {upgrade_from_version}')
            pass
        self._set_db_version(self.db_version)

    def is_table_exist(self, table_name) -> bool:
        """
        Check if a table exists.
        :param table_name: The name of the table to check.
        :return:  True if the 'assets' table exists, otherwise False.
        """
        with DatabaseConnection(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            result = cursor.fetchone()
            conn.close()
        return result is not None

    def get_row_count(self, table_name='assets') -> int:
        """
        Get the number of rows in the given table.
        :param table_name: The name of the table.
        :return:  The number of rows in the 'assets' table.
        """
        with DatabaseConnection(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
        return row_count

    def save_last_run(self, data: dict):
        """
        Save the last run data into the 'last_run' table.
        :param data: A dictionary containing the data to save.
        """
        # check if the database version is compatible with the current method
        if not self._check_db_version(VersionNum.V3, caller_name=inspect.currentframe().f_code.co_name):
            return
        with DatabaseConnection(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO last_run VALUES (?,?,?,?)", (data['date'], data['files_count'], data['items_count'], data['items_ids']))
            conn.commit()
            conn.close()

    def insert_assets(self, assets) -> None:
        """
        Insert assets into the 'assets' table.
        :param assets: A dictionary or a list of dictionaries representing assets.
        """
        # check if the database version is compatible with the current method
        if not self._check_db_version(VersionNum.V2, caller_name=inspect.currentframe().f_code.co_name):
            return
        with DatabaseConnection(self.db_name) as conn:
            cursor = conn.cursor()
            if not isinstance(assets, list):
                assets = [assets]
            for asset in assets:
                # Notes: the order of columns and value must match the order of the fields in init_data() method
                cursor.execute(
                    """
                        INSERT OR REPLACE INTO assets (id,
                        namespace,
                        catalog_item_id,
                        title,
                        category,
                        author,
                        thumbnail_url,
                        current_price_discounted,
                        asset_slug,
                        currency_code,
                        description,
                        technical_details,
                        long_description,
                        categories,
                        tags,
                        comment_rating_id,
                        rating_id,
                        status,
                        price,
                        discount,
                        discount_price,
                        discount_percentage,
                        is_featured,
                        is_catalog_item,
                        is_new,
                        free,
                        discounted,
                        can_purchase,
                        owned,
                        review,
                        review_count,
                        comment,
                        stars,
                        must_buy,
                        test_result,
                        installed_folder,
                        alternative,
                        origin
                    ) 
                    VALUES (?, ?, ?, ?, ?, ?,  ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        asset['id'],  #
                        asset['namespace'],  #
                        asset['catalog_item_id'],  #
                        asset['title'],  #
                        asset["category"],  #
                        asset['author'],  #
                        asset['thumbnail_url'],  #
                        asset['current_price_discounted'],  #
                        asset['asset_slug'],  #
                        asset['currency_code'],  #
                        asset['description'],  #
                        asset['technical_details'],  #
                        asset['long_description'],  #
                        str(asset['categories']),  # mandatory conversion to string because categories is a list
                        str(asset['tags']),  # mandatory conversion to string because tags is a list
                        asset['comment_rating_id'],  #
                        asset['rating_id'],  #
                        asset['status'],  #
                        asset['price'],  #
                        asset['discount'],  #
                        asset['discount_price'],  #
                        asset['discount_percentage'],  #
                        asset['is_featured'],  #
                        asset['is_catalog_item'],  #
                        asset['is_new'],  #
                        asset['free'],  #
                        asset['discounted'],  #
                        asset['can_purchase'],  #
                        asset['owned'],  #
                        asset['review'],  #
                        asset['review_count'],  #
                        asset['comment'],  #
                        asset['stars'],  #
                        asset['must_buy'],  #
                        asset['test_result'],  #
                        asset['installed_folder'],  #
                        asset['alternative'],  #
                        asset['origin']  #
                    )
                )

            conn.commit()

    def get_assets(self) -> list:
        """
        Get all assets from the 'assets' table.
        :return: A list of dictionaries representing assets.
        """
        with DatabaseConnection(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM assets")

            row_data = []
            for row in cursor.fetchall():
                ue_asset = UEAsset()
                ue_asset.init_from_list(data=row)
                row_data.append(ue_asset.data)

        return row_data

    def delete_asset(self, asset_id: str) -> None:
        """
        Delete an asset from the 'assets' table by its ID.
        :param asset_id: The ID of the asset to delete.
        """
        with DatabaseConnection(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
            conn.commit()

    def update_asset(self, asset_id: str, column: str, value) -> None:
        """
        Update a specific column of an asset in the 'assets' table by its ID.
        :param asset_id: The ID of the asset to update.
        :param column: The name of the column
        :param value: The new value.
        """
        with DatabaseConnection(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE assets SET {column} = ? WHERE id = ?", (value, asset_id))
            conn.commit()

    def generate_test_data(self, number_of_rows=1) -> None:
        """
        Generate and insert the specified number of fake assets into the 'assets' table.
        :param number_of_rows: The number of fake assets to generate and insert.
        """
        # check if the database version is compatible with the current method
        if not self._check_db_version(VersionNum.V2, caller_name=inspect.currentframe().f_code.co_name):
            return
        assets_ids = []
        fake = Faker()
        for index in range(number_of_rows):
            assets_id = fake.uuid4()
            print(f'creating test asset # {index} with id {assets_id}')
            ue_asset = UEAsset()
            # the order of values must match the order of the fields in init_data() method
            data_list = [
                assets_id,  # id
                fake.word(),  # namespace
                fake.uuid4(),  # catalog_item_id
                fake.sentence(),  # title
                fake.word(),  # category
                fake.name(),  # author
                fake.image_url(),  # thumbnail_url
                round(random.uniform(1, 100), 2),  # current_price_discounted
                fake.slug(),  # asset_slug
                'USD',  # currency_code
                fake.text(),  # description
                fake.text(),  # technical_details
                fake.text(),  # long_description
                [{
                    'name': fake.word()
                }],  # categories
                [fake.word(), fake.word()],  # tags
                fake.uuid4(),  # comment_rating_id
                fake.uuid4(),  # rating_id
                fake.word(),  # status
                round(random.uniform(1, 100), 2),  # price
                round(random.uniform(1, 100), 2),  # discount
                round(random.uniform(1, 100), 2),  # discount_price
                round(random.uniform(0, 100), 2),  # discount_percentage
                random.choice([0, 1]),  # is_featured
                random.choice([0, 1]),  # is_catalog_item
                random.choice([0, 1]),  # is_new
                random.choice([0, 1]),  # free
                random.choice([0, 1]),  # discounted
                random.choice([0, 1]),  # can_purchase
                random.choice([0, 1]),  # owned
                round(random.uniform(0, 5), 1),  # review
                random.randint(0, 1000),  # review_count
                fake.text(),  # comment
                random.randint(1, 5),  # stars
                random.choice([0, 1]),  # must_buy
                fake.word(),  # test_result
                fake.file_path(),  # installed_folder
                fake.sentence(),  # alternative
                fake.word()  # origin
            ]
            ue_asset.init_from_list(data=data_list)
            self.insert_assets(ue_asset.data)
            assets_ids.append(assets_id)
        content = {'date': str(datetime.datetime.now()), 'files_count': 0, 'items_count': number_of_rows, 'items_ids': ','.join(assets_ids)}
        self.save_last_run(content)


class UEAsset:
    """
    A class to represent an Unreal Engine asset. With the EGS data and user data.
    """

    def __init__(self):
        self.data = {}
        self.user_data = {}
        self.log = logging.getLogger('UEAsset')
        self.log.setLevel(logging.INFO)
        self.init_data()

    def init_data(self) -> None:
        """
        Initialize the EGS data dictionary.
        """
        self.data = {
            'id': None,
            'namespace': None,
            'catalog_item_id': None,
            'title': None,
            "category": None,
            # 'category_slug': None,
            'author': None,
            'thumbnail_url': None,
            'current_price_discounted': None,
            'asset_slug': None,
            'currency_code': None,
            'description': None,
            'technical_details': None,
            'long_description': None,
            'categories': None,
            'tags': None,
            'comment_rating_id': None,
            'rating_id': None,
            'status': None,
            'price': None,
            'discount': None,
            # 'discount_price':data['discountPrice'],
            # 'discount_price_value':data[ 'discountPriceValue'],
            'discount_price': None,
            # 'voucher_discount':data[ 'voucherDiscount'],
            'discount_percentage': None,
            'is_featured': None,
            'is_catalog_item': None,
            'is_new': None,
            'free': None,
            'discounted': None,
            'can_purchase': None,
            'owned': None,
            'review': None,
            'review_count': None,
            'comment': None,
            'stars': None,
            'must_buy': None,
            'test_result': None,
            'installed_folder': None,
            'alternative': None,
            'origin': None
        }

    def init_from_dict(self, data: dict = None) -> None:
        """
        Initialize the asset data from the given dictionaries.
        :param data: source dictionary for the EGS data
        """
        if data:
            self.init_data()
            # copy all the keys from the data dict to the self.data dict
            init_dict_from_data(self.data, data)

    def init_from_list(self, data: list = None) -> None:
        """
        Initialize the asset data from the given lists.
        :param data: source list for the EGS data
        """
        if data:
            # create empty dictionary
            self.init_data()
            # fill dictionary with data from list
            self.data = dict(zip(self.data.keys(), data))


if __name__ == "__main__":
    # the following code is just for class testing purposes
    db_folder = path_from_relative_to_absolute('../../../scraping/')
    db_name = os.path.join(db_folder, 'assets.db')
    check_and_create_path(db_name)
    asset_handler = UEAssetDbHandler(db_name)

    rows_count = asset_handler.get_row_count()
    print(f"Rows count: {rows_count}")
    rows_to_create = 800 - rows_count
    print(f"Creating {rows_to_create} rows")
    asset_handler.generate_test_data(rows_to_create)

    # Read assets
    # asset_list = asset_handler.get_assets()
    # print("Assets:", asset_list)
