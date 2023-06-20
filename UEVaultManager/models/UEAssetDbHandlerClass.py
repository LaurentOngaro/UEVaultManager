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

from UEVaultManager.core import default_datetime_format
from UEVaultManager.models.csv_data import get_sql_field_name_list
from UEVaultManager.models.UEAssetClass import UEAsset
from UEVaultManager.tkgui.modules.functions_no_deps import path_from_relative_to_absolute
from UEVaultManager.utils.cli import check_and_create_path

test_only_mode = True  # create some limitations to speed up the dev process - Set to True for debug Only


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
    V4 = 4  # add custom_attributes field to the assets table
    V5 = 5  # future version


class DatabaseConnection:
    """
    Context manager for opening and closing a database connection
    :param database_name: The name of the database file.
    """

    def __init__(self, database_name: str):
        self.database_name = database_name
        self.conn = sqlite3.connect(self.database_name)

    def __enter__(self):
        """
        Open the database connection.
        :return: The sqlite3.Connection object.
        """
        self.conn = sqlite3.connect(self.database_name)
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Close the database connection.
        :param exc_type: Exception type.
        :param exc_val: Exception value.
        :param exc_tb: Exception traceback.
        """
        self.conn.close()
        self.conn = None


class UEAssetDbHandler:
    """
    Handles database operations for the UE Assets.
    :param database_name: The name of the database file.
    :param reset_database: If True, the database will be reset.

    Note: The database will be created if it doesn't exist.
    """

    def __init__(self, database_name: str, reset_database: bool = False):
        self.logger = logging.getLogger(__name__)
        # self.logger.setLevel(logging.DEBUG)
        self.database_name = database_name
        self.db_version = VersionNum.V0  # updated in check_and_upgrade_database()
        # the user fields that must be preserved when updating the database
        # these fields are also present in the asset table and in the UEAsset.init_data() method
        # THEY WILL BE PRESERVED when parsing the asset data
        self.user_fields = ['comment', 'stars', 'must_buy', 'test_result', 'installed_folder', 'alternative', 'origin']
        # the field we keep for previous data. NEED TO BE SEPARATED FROM self.user_fields
        # THEY WILL BE USED (BUT NOT FORCELY PRESERVED) when parsing the asset data
        self.existing_data_fields = ['id', 'price', 'old_price', 'asset_url', 'grab_result', 'date_added_in_db']
        self.existing_data_fields.extend(self.user_fields)
        self.connection = None
        self._init_connection()
        if reset_database:
            self.drop_tables()

        self.check_and_upgrade_database()

    def __del__(self):
        # log could alrready be destroyed before here
        # self.logger.debug('Deleting UEAssetDbHandler and closing connection')
        print('Deleting UEAssetDbHandler and closing connection')
        self._close_connection()

    def _close_connection(self) -> None:
        """
        Close the database connection.
        """
        if self.connection is not None:
            self.connection.close()
        self.connection = None

    def _init_connection(self) -> sqlite3.Connection:
        """
        Initialize the database connection.
        :return: The sqlite3.Connection object.

        Note: It will also set self.Connection property.
        """
        self._close_connection()  # close the connection IF IT WAS ALREADY OPENED
        try:
            self.connection = DatabaseConnection(self.database_name).conn
        except sqlite3.Error as error:
            print(f'Error while connecting to sqlite: {error!r}')

        return self.connection

    def _get_db_version(self) -> VersionNum:
        """
        Check the database version.
        :return: The database version.
        """
        try:
            if self.connection is not None:
                cursor = self.connection.cursor()
                cursor.execute("PRAGMA user_version")
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
        if self.connection is not None:
            cursor = self.connection.cursor()
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

    def _add_missing_columns(self, table_name: str, required_columns: dict) -> None:
        """
        Add missing columns to a table.
        :param table_name: Name of the table.
        :param required_columns: Dictionary of columns to add. Key is the column name, value is the data type.
        """
        if self.connection is not None:
            cursor = self.connection.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = {row[1]: row for row in cursor.fetchall()}
            for column_name, data_type in required_columns.items():
                if column_name not in columns:
                    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {data_type}")
            self.connection.commit()

    def db_exists(self) -> bool:
        """
        Check if the database file exists.
        :return: True if the database file exists, otherwise False.
        """
        return os.path.exists(self.database_name)

    def create_tables(self, upgrade_to_version=VersionNum.V1) -> None:
        """
        Create the tables if they don't exist.
        :param upgrade_to_version: The database version we want to upgrade TO
        """
        # all the following steps must be run sequentially
        if upgrade_to_version.value >= VersionNum.V1.value:
            if not self.is_table_exist('assets'):
                if self.connection is not None:
                    cursor = self.connection.cursor()
                    # create the first version of the database
                    # Note:
                    # - this table has the same structure as the json files saved inside the method UEAssetScraper.save_to_file()
                    # - the order of columns must match the order of the fields in UEAsset.init_data() method
                    query = """
                    CREATE TABLE IF NOT EXISTS assets ( 
                        id TEXT PRIMARY KEY, 
                        namespace TEXT, 
                        catalog_item_id TEXT, 
                        title TEXT, 
                        category TEXT, 
                        author TEXT, 
                        thumbnail_url TEXT, 
                        asset_slug TEXT, 
                        currency_code TEXT, 
                        description TEXT, 
                        technical_details TEXT, 
                        long_description TEXT, 
                        tags TEXT, 
                        comment_rating_id TEXT, 
                        rating_id TEXT, 
                        status TEXT, 
                        price REAL, 
                        discount_price REAL, 
                        discount_percentage REAL, 
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
                    cursor.execute(query)
                    self.connection.commit()
        if upgrade_to_version.value >= VersionNum.V3.value:
            if not self.is_table_exist('last_run'):
                # Note: this table has the same structure as the data saved in the last_run_filename inside the method UEAssetScraper.save_all_to_files()
                cursor = self.connection.cursor()
                query = "CREATE TABLE IF NOT EXISTS last_run (date DATETIME, mode TEXT, files_count INTEGER, items_count INTEGER, scrapped_ids TEXT)"
                cursor.execute(query)
                self.connection.commit()

    def check_and_upgrade_database(self, upgrade_from_version: VersionNum = None) -> None:
        """
        Change the tables structure according to different versions.
        :param upgrade_from_version: The version we want to upgrade FROM. if None, the current version will be used
        """
        if not self.is_table_exist('assets'):
            previous_version = VersionNum.V0
        else:
            # force an update of the db_version property
            previous_version = self._get_db_version()
            # if self.db_version == VersionNum.V0:
            #    raise Exception("Invalid database version or database is badly initialized")

        self.db_version = previous_version
        if upgrade_from_version is None:
            upgrade_from_version = self.db_version

        # all the following steps must be run sequentially
        if upgrade_from_version.value <= VersionNum.V1.value:
            # necessary steps to upgrade to version 1, aka create tables
            self.create_tables(upgrade_to_version=VersionNum.V1)
            # necessary steps to upgrade to version 2
            # add the columns used fo user data to the "standard" marketplace columns
            self._add_missing_columns(
                'assets',
                required_columns={
                    'asset_id': 'TEXT',
                    'asset_url': 'TEXT',
                    'comment': 'TEXT',
                    'stars': 'INTEGER',
                    'must_buy': 'BOOL',
                    'test_result': 'TEXT',
                    'installed_folder': 'TEXT',
                    'alternative': 'TEXT',
                    'origin': 'TEXT',
                    'page_title': 'TEXT',
                    'obsolete': 'BOOL',
                    'supported_versions': 'TEXT',
                    'creation_date': 'DATETIME',
                    'update_date': 'DATETIME',
                    'date_added_in_db': 'DATETIME',
                    'grab_result': 'TEXT',
                    'old_price': 'REAL'
                }
            )
            self.db_version = VersionNum.V2
            upgrade_from_version = self.db_version
            self.logger.info(f'Database upgraded to {upgrade_from_version}')
        if upgrade_from_version == VersionNum.V2:
            # necessary steps to upgrade to version 3
            # add the last_run table to get data about the last run of the ap
            self.create_tables(upgrade_to_version=VersionNum.V3)
            self.db_version = VersionNum.V3
            upgrade_from_version = self.db_version
            self.logger.info(f'Database upgraded to {upgrade_from_version}')
        if upgrade_from_version == VersionNum.V3:
            # necessary steps to upgrade to version 4
            self._add_missing_columns('assets', required_columns={'custom_attributes': 'TEXT'})
            self.db_version = VersionNum.V4
            upgrade_from_version = self.db_version
            self.logger.info(f'Database upgraded to {upgrade_from_version}')
        if upgrade_from_version == VersionNum.V4:
            # necessary steps to upgrade to version 5
            # does not exist yet
            # do stuff here
            # self.db_version = VersionNum.V5
            # upgrade_from_version = self.db_version
            # self.logger.info(f'Database upgraded to {upgrade_from_version}')
            pass
        if previous_version != self.db_version:
            self._set_db_version(self.db_version)

    def is_table_exist(self, table_name) -> bool:
        """
        Check if a table exists.
        :param table_name: The name of the table to check.
        :return:  True if the 'assets' table exists, otherwise False.
        """
        result = None
        if self.connection is not None:
            cursor = self.connection.cursor()
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            result = cursor.fetchone()
        return result is not None

    def get_rows_count(self, table_name='assets') -> int:
        """
        Get the number of rows in the given table.
        :param table_name: The name of the table.
        :return:  The number of rows in the 'assets' table.
        """
        row_count = 0
        if self.connection is not None:
            cursor = self.connection.cursor()
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
        if self.connection is not None:
            cursor = self.connection.cursor()
            query = "INSERT INTO last_run (date, mode, files_count, items_count, scrapped_ids) VALUES (:date, :mode, :files_count, :items_count, :scrapped_ids)"
            cursor.execute(query, data)
            self.connection.commit()

    def set_assets(self, assets) -> None:
        """
        Insert or update assets into the 'assets' table.
        :param assets: A dictionary or a list of dictionaries representing assets.

        NOTE: the (existing) user fields data should have already been added or merged the assets dictionary
        """
        # check if the database version is compatible with the current method
        if not self._check_db_version(VersionNum.V2, caller_name=inspect.currentframe().f_code.co_name):
            return
        if self.connection is not None:
            cursor = self.connection.cursor()
            if not isinstance(assets, list):
                assets = [assets]
            date_added_in_db = datetime.datetime.now().strftime(default_datetime_format)
            # Note: the order of columns and value must match the order of the fields in UEAsset.init_data() method
            for asset in assets:
                if asset.get('date_added_in_db', None) is None:
                    asset['date_added_in_db'] = date_added_in_db

                # Generate the SQL query
                # this query will insert or update the asset if it already exists
                query = """
                    REPLACE INTO assets (
                        id, namespace, catalog_item_id, title, category, author, thumbnail_url,
                        asset_slug, currency_code, description,
                        technical_details, long_description, tags, comment_rating_id,
                        rating_id, status, price, discount_price, discount_percentage,
                        is_catalog_item, is_new, free, discounted, can_purchase,
                        owned, review, review_count, asset_id, asset_url,
                        comment, stars, must_buy, test_result, installed_folder, alternative, origin, page_title,
                        obsolete, supported_versions, creation_date, update_date, date_added_in_db, grab_result,
                        old_price, custom_attributes
                    ) VALUES (
                        :id, :namespace, :catalog_item_id, :title, :category, :author, :thumbnail_url,
                        :asset_slug, :currency_code, :description,
                        :technical_details, :long_description, :tags, :comment_rating_id,
                        :rating_id, :status, :price, :discount_price, :discount_percentage,
                        :is_catalog_item, :is_new, :free, :discounted, :can_purchase,
                        :owned, :review, :review_count, :asset_id, :asset_url,
                        :comment, :stars, :must_buy, :test_result, :installed_folder, :alternative, :origin, :page_title, 
                        :obsolete, :supported_versions, :creation_date, :update_date, :date_added_in_db, :grab_result,
                        :old_price, :custom_attributes
                    )
                """
                # Execute the SQL query
                try:
                    cursor.execute(query, asset)
                except (sqlite3.IntegrityError, sqlite3.InterfaceError) as error:
                    self.logger.error(f"Error while inserting/updating asset '{asset['id']}' (tags='{asset['tags']}': {error!r}")
            self.connection.commit()

    def get_assets_data(self, fields='*') -> dict:
        """
        Get data from all the assets in the 'assets' table.
        :param fields: list of fields to return.
        :return: dictionary {ids, rows}
        """
        if not isinstance(fields, str):
            fields = ', '.join(fields)
        row_data = {}
        if self.connection is not None:
            self.connection.row_factory = sqlite3.Row
            cursor = self.connection.cursor()
            cursor.execute(f"SELECT {fields} FROM assets")
            for row in cursor.fetchall():
                uid = row['id']
                row_data[uid] = dict(row)
        return row_data

    def get_assets_data_for_csv(self) -> (list, list):
        """
        Get data from all the assets in the 'assets' table for a "CSV file" like format.
        :return: list(rows),list (column_names)
        """
        csv_column_names = []
        rows = []
        if self.connection is not None:
            cursor = self.connection.cursor()
            # generate column names for the CSV file using AS to rename the columns
            fields = get_sql_field_name_list(exclude_csv_only=True, return_as_string=True, add_alias=True)
            query = f"SELECT {fields} FROM assets"
            if test_only_mode:
                query += ' ORDER BY date_added_in_db DESC LIMIT 3000'
            cursor.execute(query)
            rows = cursor.fetchall()
            csv_column_names = [
                description[0] for description in cursor.description
            ]  # by using the 'AS' in the SQL query, the column names are the CSV column names
            cursor.close()

        return rows, csv_column_names

    def create_empty_row(self, return_as_string=True, empty_cell='None'):
        """
        Create an empty row in the 'assets' table.
        :param return_as_string: True to return the row as a string, False to
        :param empty_cell: The value to use for empty cells.
        :return: A row (dict) or a string representing the empty row.
        """
        result = '' if return_as_string else {}
        # add a new row to the 'assets' table
        if self.connection is not None:
            cursor = self.connection.cursor()
            cursor.execute("INSERT INTO assets DEFAULT VALUES")
            self.connection.commit()
            uid = cursor.lastrowid
            ue_asset = self.get_ue_asset(str(uid))
            ue_asset.asset_id = 'dummy_row_' + str(uid)  # dummy unique Asset_id to avoid issue
            ue_asset.thumbnail_url = empty_cell  # avoid displaying image warning on mouse over
            result = str(ue_asset) if return_as_string else ue_asset
        return result

    def get_ue_asset(self, uid: str) -> UEAsset:
        """
        Get an asset from the 'assets' table.
        :param uid: The ID of the asset to get.
        :return: an UEAsset object.
        """
        ue_asset = None
        if self.connection is not None:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * assets WHERE id = ?", (uid,))

            row = cursor.fetchone()
            ue_asset = UEAsset()
            ue_asset.init_from_list(data=row)

        return ue_asset

    def delete_asset(self, uid: str) -> None:
        """
        Delete an asset from the 'assets' table by its ID.
        :param uid: The ID of the asset to delete.
        """
        if self.connection is not None:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM assets WHERE id = ?", (uid,))
            self.connection.commit()

    def delete_all_assets(self) -> None:
        """
        Delete all assets from the 'assets' table.
        """
        if self.connection is not None:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM assets WHERE 1")
            self.connection.commit()

    def update_asset(self, uid: str, column: str, value) -> None:
        """
        Update a specific column of an asset in the 'assets' table by its ID.
        :param uid: The ID of the asset to update.
        :param column: The name of the column
        :param value: The new value.
        """
        if self.connection is not None:
            cursor = self.connection.cursor()
            cursor.execute(f"UPDATE assets SET {column} = ? WHERE id = ?", (value, uid))
            self.connection.commit()

    def drop_tables(self) -> None:
        """
        Drop the 'assets' and 'last_run' tables.
        """
        if self.connection is not None:
            cursor = self.connection.cursor()
            cursor.execute("DROP TABLE IF EXISTS assets")
            cursor.execute("DROP TABLE IF EXISTS last_run")
            self.connection.commit()

    def generate_test_data(self, number_of_rows=1) -> None:
        """
        Generate and insert the specified number of fake assets into the 'assets' table.
        :param number_of_rows: The number of fake assets to generate and insert.
        """
        # check if the database version is compatible with the current method
        if not self._check_db_version(VersionNum.V2, caller_name=inspect.currentframe().f_code.co_name):
            return
        scraped_ids = []
        fake = Faker()
        for index in range(number_of_rows):
            assets_id = fake.uuid4()
            print(f'creating test asset # {index} with id {assets_id}')
            ue_asset = UEAsset()
            # the order of values must match the order of the fields in csv_data.py/csv_sql_fields dict
            data_list = [
                fake.uuid4(),  # asset_id
                fake.sentence(),  # title
                fake.word(),  # category
                round(random.uniform(0, 5), 1),  # review
                random.randint(0, 1000),  # review_count
                fake.name(),  # author
                fake.text(),  # description
                fake.word(),  # status
                round(random.uniform(1, 100), 2),  # discount_price
                round(random.uniform(0, 100), 2),  # discount_percentage
                random.choice([0, 1]),  # discounted
                random.choice([0, 1]),  # is_new
                random.choice([0, 1]),  # free
                random.choice([0, 1]),  # can_purchase
                random.choice([0, 1]),  # owned
                random.choice([0, 1]),  # obsolete
                fake.word(),  # supported_versions
                fake.word(),  # grab_result
                round(random.uniform(1, 100), 2),  # price
                random.randint(0, 1000),  # old_price
                fake.text(),  # comment
                random.randint(1, 5),  # stars
                random.choice([0, 1]),  # must_buy
                fake.word(),  # test_result
                fake.file_path(),  # installed_folder
                fake.sentence(),  # alternative
                fake.word(),  # origin
                fake.sentence(),  # custom_attributes
                fake.sentence(),  # page_title
                fake.image_url(),  # thumbnail_url
                fake.url(),  # asset_url
                fake.date_time(),  # creation_date
                fake.date_time(),  # update_date
                fake.date_time(),  # date_added_in_db
                assets_id,  # id
                fake.word(),  # namespace
                fake.uuid4(),  # catalog_item_id
                fake.slug(),  # asset_slug
                'USD',  # currency_code
                fake.text(),  # technical_details
                fake.text(),  # long_description
                [random.randint(0, 1000), random.randint(0, 1000), random.randint(0, 1000)],  # tags
                fake.uuid4(),  # comment_rating_id
                fake.uuid4(),  # rating_id
                random.choice([0, 1]),  # is_catalog_item
            ]
            ue_asset.init_from_list(data=data_list)
            self.set_assets(assets=ue_asset.data)
            scraped_ids.append(assets_id)
        content = {
            'date': datetime.datetime.now().strftime(default_datetime_format),
            'mode': 'save',
            'files_count': 0,
            'items_count': number_of_rows,
            'scrapped_ids': ','.join(scraped_ids)
        }
        self.save_last_run(content)


if __name__ == "__main__":
    # the following code is just for class testing purposes
    clean_data = True
    read_data_only = False  # if True, the code will not create fake assets, but only read them from the database

    db_folder = path_from_relative_to_absolute('../../../scraping/')
    db_name = os.path.join(db_folder, 'assets.db')
    check_and_create_path(db_name)
    asset_handler = UEAssetDbHandler(database_name=db_name, reset_database=(clean_data and not read_data_only))

    if read_data_only:
        # Read existing assets
        asset_list = asset_handler.get_assets_data()
        print("Assets:", asset_list)
    else:
        # Create fake assets
        rows_to_create = 300
        if not clean_data:
            rows_count = asset_handler.get_rows_count()
            print(f"Rows count: {rows_count}")
            rows_to_create -= rows_count
        print(f"Creating {rows_to_create} rows")
        asset_handler.generate_test_data(rows_to_create)

    rows_count = asset_handler.get_rows_count()
    print(f"FINAL Rows count: {rows_count}")
