# coding=utf-8
"""
implementation for:
- UEAssetDbHandler: Handles database operations for the UE Assets.
"""
import datetime
import inspect
import logging
import os
import random
import sqlite3

from faker import Faker

from UEVaultManager.core import default_datetime_format
from UEVaultManager.models.csv_sql_fields import get_sql_field_name_list, CSVFieldState
from UEVaultManager.models.types import DbVersionNum
from UEVaultManager.models.UEAssetClass import UEAsset
from UEVaultManager.tkgui.modules.functions_no_deps import path_from_relative_to_absolute, convert_to_str_datetime, create_uid
from UEVaultManager.utils.cli import check_and_create_path

test_only_mode = False  # add some limitations to speed up the dev process - Set to True for Debug Only


class UEAssetDbHandler:
    """
    Handles database operations for the UE Assets.
    :param database_name: The name of the database file.
    :param reset_database: If True, the database will be reset.

    Note: The database will be created if it doesn't exist.
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    db_version: DbVersionNum = DbVersionNum.V0  # updated in check_and_upgrade_database()
    connection = None

    def __init__(self, database_name: str, reset_database: bool = False):
        # the user fields that must be preserved when updating the database
        # these fields are also present in the asset table and in the UEAsset.init_data() method
        # THEY WILL BE PRESERVED when parsing the asset data
        self.user_fields = get_sql_field_name_list(filter_on_states=[CSVFieldState.USER])
        # the field we keep for previous data. NEED TO BE SEPARATED FROM self.user_fields
        # THEY WILL BE USED (BUT NOT FORCELY PRESERVED) when parsing the asset data
        self.preserved_data_fields = self.user_fields
        self.preserved_data_fields.append('id')
        changed_fields = get_sql_field_name_list(filter_on_states=[CSVFieldState.CHANGED])
        self.preserved_data_fields.extend(changed_fields)
        # we also need to preserve the values in the database that are not in the (CSV) table
        asset_fields = get_sql_field_name_list(filter_on_states=[CSVFieldState.ASSET_ONLY])
        self.preserved_data_fields.extend(asset_fields)
        self.database_name: str = database_name
        self._init_connection()
        if reset_database:
            self.drop_tables()

        self.check_and_upgrade_database()

    class DatabaseConnection:
        """
        Context manager for opening and closing a database connection.
        :param database_name: The name of the database file.
        """

        def __init__(self, database_name: str):
            self.database_name: str = database_name
            self.conn = sqlite3.connect(self.database_name, check_same_thread=False)

        def __enter__(self):
            """
            Open the database connection.
            :return: The sqlite3.Connection object.
            """
            self.conn = sqlite3.connect(self.database_name, check_same_thread=False)
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
            try:
                self.connection.close()
            except sqlite3.Error as error:
                print(f'Error while closing sqlite connection: {error!r}')
        self.connection = None

    def _init_connection(self) -> sqlite3.Connection:
        """
        Initialize the database connection.
        :return: The sqlite3.Connection object.

        Note: It will also set self.Connection property.
        """
        self._close_connection()  # close the connection IF IT WAS ALREADY OPENED
        try:
            self.connection = self.DatabaseConnection(self.database_name).conn
        except sqlite3.Error as error:
            print(f'Error while connecting to sqlite: {error!r}')

        return self.connection

    def _get_db_version(self) -> DbVersionNum:
        """
        Check the database version.
        :return: The database version.
        """
        try:
            if self.connection is not None:
                cursor = self.connection.cursor()
                cursor.execute("PRAGMA user_version")
                ret = int(cursor.fetchone()[0])  # type: int
                cursor.close()
                db_version = DbVersionNum(ret)
                return db_version
        except sqlite3.OperationalError:
            self.logger.critical('Could not get the database version')
            return DbVersionNum.V0

    def _set_db_version(self, new_version: DbVersionNum) -> None:
        """
        Set the database version.
        :param new_version: The new database version.
        """
        if self.connection is not None:
            cursor = self.connection.cursor()
            cursor.execute(f'PRAGMA user_version = {new_version.value}')
            cursor.close()
            self.logger.info(f'database version is now set to {new_version}')

    def _check_db_version(self, minimal_db_version: DbVersionNum, caller_name='this method') -> bool:
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

        NOTE: the AFTER parameter in SQL is not supported in the SQLite version used.
        """
        if self.connection is not None:
            cursor = self.connection.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = {row[1]: row for row in cursor.fetchall()}
            for column_name, data_type in required_columns.items():
                if column_name not in columns:
                    query = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {data_type}"
                    cursor.execute(query)
            self.connection.commit()
            cursor.close()

    def db_exists(self) -> bool:
        """
        Check if the database file exists.
        :return: True if the database file exists, otherwise False.
        """
        return os.path.exists(self.database_name)

    def create_tables(self, upgrade_to_version=DbVersionNum.V1) -> None:
        """
        Create the tables if they don't exist.
        :param upgrade_to_version: The database version we want to upgrade TO.
        """
        # all the following steps must be run sequentially
        if upgrade_to_version.value >= DbVersionNum.V1.value:
            if self.connection is not None:
                cursor = self.connection.cursor()
                # create the first version of the database
                # Note:
                # - this table has the same structure as the json files saved inside the method UEAssetScraper.save_to_file()
                # - the order of columns must match the order of the fields in UEAsset.init_data() method.
                query = """
                CREATE TABLE IF NOT EXISTS assets ( 
                    id TEXT PRIMARY KEY NOT NULL, 
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
                    review_count INTEGER,
                    custom_attributes TEXT
                )
                """
                cursor.execute(query)
                self.connection.commit()
                cursor.close()
        if upgrade_to_version.value >= DbVersionNum.V3.value:
            cursor = self.connection.cursor()
            query = "CREATE TABLE IF NOT EXISTS last_run (date DATETIME, mode TEXT, files_count INTEGER, items_count INTEGER, scraped_ids TEXT)"
            cursor.execute(query)
            self.connection.commit()
            cursor.close()
        if upgrade_to_version.value >= DbVersionNum.V7.value:
            cursor = self.connection.cursor()
            query = "CREATE TABLE IF NOT EXISTS tags (id INTEGER PRIMARY KEY NOT NULL, name TEXT)"
            cursor.execute(query)
            self.connection.commit()
            cursor.close()
        if upgrade_to_version.value >= DbVersionNum.V8.value:
            cursor = self.connection.cursor()
            query = "CREATE TABLE IF NOT EXISTS ratings (id TEXT PRIMARY KEY NOT NULL, averageRating REAL, total INTEGER)"
            cursor.execute(query)
            self.connection.commit()
            cursor.close()
        if upgrade_to_version.value >= DbVersionNum.V9.value:
            cursor = self.connection.cursor()
            query = """
                    CREATE VIEW IF NOT EXISTS assets_tags AS
                    WITH RECURSIVE split(asset_id, tags, tag, rest) AS (
                        SELECT asset_id, tags, '', tags || ','
                        FROM assets
                        UNION ALL
                        SELECT asset_id, tags, substr(rest, 0, instr(rest, ',')), substr(rest, instr(rest, ',')+1)
                        FROM split
                        WHERE rest <> ''
                    )
                    SELECT asset_id, tag FROM split WHERE tag <> '';
                    """
            cursor.execute(query)
            self.connection.commit()
            cursor.close()

    def check_and_upgrade_database(self, upgrade_from_version: DbVersionNum = None) -> None:
        """
        Change the tables structure according to different versions.
        :param upgrade_from_version: The version we want to upgrade FROM. if None, the current version will be used.
        """
        if not self.is_table_exist('assets'):
            previous_version = DbVersionNum.V0
        elif not self.is_table_exist('tags'):
            previous_version = DbVersionNum.V6
        elif not self.is_table_exist('ratings'):
            previous_version = DbVersionNum.V7
        else:
            # force an update of the db_version property
            previous_version = self._get_db_version()
            # if self.db_version == DbVersionNum.V0:
            #    raise Exception("Invalid database version or database is badly initialized")

        self.db_version = previous_version

        if upgrade_from_version is None:
            upgrade_from_version = self.db_version

        # all the following steps must be run sequentially
        if upgrade_from_version.value <= DbVersionNum.V1.value:
            # necessary steps to upgrade to version 1, aka create tables
            self.db_version = DbVersionNum.V2
            self.create_tables(upgrade_to_version=self.db_version)
        if upgrade_from_version == DbVersionNum.V2:
            # necessary steps to upgrade from version 2
            # add the last_run table to get data about the last run of the ap
            self.db_version = DbVersionNum.V3
            self.create_tables(upgrade_to_version=self.db_version)
        if upgrade_from_version == DbVersionNum.V3:
            # necessary steps to upgrade from version 3
            # add user fields
            self._add_missing_columns(
                'assets',
                required_columns={
                    'asset_id': 'TEXT',
                    'asset_url': 'TEXT',
                    'comment': 'TEXT',
                    'stars': 'INTEGER',
                    'must_buy': 'BOOLEAN',
                    'test_result': 'TEXT',
                    'installed_folder': 'TEXT',
                    'alternative': 'TEXT',
                    'origin': 'TEXT',
                    'added_manually': 'BOOLEAN'
                }
            )
            self.db_version = DbVersionNum.V4
            upgrade_from_version = self.db_version
        if upgrade_from_version == DbVersionNum.V4:
            # necessary steps to upgrade from version 4
            # add changed fields
            self._add_missing_columns(
                'assets',
                required_columns={
                    'added_manually': 'BOOLEAN',
                    'page_title': 'TEXT',
                    'obsolete': 'BOOLEAN',
                    'supported_versions': 'TEXT',
                    'creation_date': 'DATETIME',
                    'update_date': 'DATETIME',
                    'date_added_in_db': 'DATETIME',
                    'grab_result': 'TEXT',
                    'old_price': 'REAL'
                }
            )
            self.db_version = DbVersionNum.V5
        if upgrade_from_version == DbVersionNum.V5:
            # necessary steps to upgrade from version 5
            # add changed fields
            self._add_missing_columns('assets', required_columns={'tags': 'TEXT', })
            self.db_version = DbVersionNum.V6
        if upgrade_from_version == DbVersionNum.V6:
            self.db_version = DbVersionNum.V7
            self.create_tables(upgrade_to_version=self.db_version)
        if upgrade_from_version == DbVersionNum.V7:
            self.db_version = DbVersionNum.V8
            self.create_tables(upgrade_to_version=self.db_version)
        if upgrade_from_version == DbVersionNum.V8:
            self.db_version = DbVersionNum.V9
            self.create_tables(upgrade_to_version=self.db_version)
        if upgrade_from_version == DbVersionNum.V9:
            """
            necessary steps to upgrade from version 9
            does not exist yet
            """
            """
            # do some stuff here
            self.db_version = DbVersionNum.V10
            """
            pass
        if previous_version != self.db_version:
            self.logger.info(f'Database upgraded to {self.db_version}')
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
            cursor.close()
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
            cursor.close()
        return row_count

    # noinspection DuplicatedCode
    def save_last_run(self, data: dict):
        """
        Save the last run data into the 'last_run' table.
        :param data: A dictionary containing the data to save.
        """
        # check if the database version is compatible with the current method
        if not self._check_db_version(DbVersionNum.V3, caller_name=inspect.currentframe().f_code.co_name):
            return
        if self.connection is not None:
            cursor = self.connection.cursor()
            query = "INSERT INTO last_run (date, mode, files_count, items_count, scraped_ids) VALUES (:date, :mode, :files_count, :items_count, :scraped_ids)"
            cursor.execute(query, data)
            cursor.close()
            self.connection.commit()

    def set_assets(self, assets) -> None:
        """
        Insert or update assets into the 'assets' table.
        :param assets: A dictionary or a list of dictionaries representing assets.

        NOTE: the (existing) user fields data should have already been added or merged the asset dictionary.
        """
        # check if the database version is compatible with the current method
        if not self._check_db_version(DbVersionNum.V2, caller_name=inspect.currentframe().f_code.co_name):
            return
        if self.connection is not None:
            cursor = self.connection.cursor()
            if not isinstance(assets, list):
                assets = [assets]
            str_today = datetime.datetime.now().strftime(default_datetime_format)
            # Note: the order of columns and value must match the order of the fields in UEAsset.init_data() method
            for asset in assets:
                asset['update_date'] = str_today
                asset['creation_date'] = convert_to_str_datetime(value=asset['creation_date'], date_format=default_datetime_format)
                asset['date_added_in_db'] = convert_to_str_datetime(
                    value=asset['date_added_in_db'], date_format=default_datetime_format, default=str_today
                )
                tags = asset.get('tags', [])
                tags_str = self.convert_tag_list_to_string(tags)
                asset['tags'] = tags_str
                # remove all fields whith a None Value
                filtered_fields = {k: v for k, v in asset.items() if (v is not None and v != 'None')}
                if len(filtered_fields) == 0:
                    return
                # ckeck if the asset already exists in the database
                cursor.execute(f"SELECT id FROM assets WHERE id='{asset['id']}'")
                result = cursor.fetchone()
                if result is None:
                    # asset does not exist in the database, add it
                    fields = ", ".join(f"{column}" for column in filtered_fields.keys())
                    values = ", ".join(f":{column}" for column in filtered_fields.keys())
                    # this query will insert or update the asset if it already exists.
                    # noinspection SqlInsertValues
                    query = f"REPLACE INTO assets ({fields}) VALUES ({values})"
                else:
                    # asset already exists in the database, update it
                    fields = ", ".join(f"{column} = :{column}" for column in filtered_fields.keys())
                    query = f"UPDATE assets SET {fields} WHERE id='{asset['id']}'"
                try:
                    cursor.execute(query, asset)
                except (sqlite3.IntegrityError, sqlite3.InterfaceError) as error:
                    self.logger.warning(f"Error while inserting/updating asset '{asset['id']}' (tags='{asset['tags']}': {error!r}")
        try:
            self.connection.commit()
        except (sqlite3.IntegrityError, sqlite3.InterfaceError) as error:
            self.logger.warning(f'Error when committing the database changes: {error!r}')

    def get_assets_data(self, fields='*', uid=None) -> dict:
        """
        Get data from all the assets in the 'assets' table.
        :param fields: list of fields to return.
        :param uid: The id of the asset to get data for. If None, all the assets will be returned.
        :return: dictionary {ids, rows}.
        """
        if not isinstance(fields, str):
            fields = ', '.join(fields)
        row_data = {}
        where_clause = f"WHERE id='{uid}'" if id is not None else ''
        if self.connection is not None:
            self.connection.row_factory = sqlite3.Row
            cursor = self.connection.cursor()
            cursor.execute(f"SELECT {fields} FROM assets {where_clause}")
            for row in cursor.fetchall():
                uid = row['id']
                row_data[uid] = dict(row)
            cursor.close()
        return row_data

    def get_assets_data_for_csv(self, where_clause='') -> list:
        """
        Get data from all the assets in the 'assets' table for a "CSV file" like format.
        :param where_clause: A string containing the WHERE clause to use in the SQL query.
        :return: list(rows).
        """
        rows = []
        if self.connection is not None:
            cursor = self.connection.cursor()
            # generate column names for the CSV file using AS to rename the columns
            fields = get_sql_field_name_list(exclude_csv_only=True, return_as_string=True, add_alias=True)
            query = f"SELECT {fields} FROM assets"
            if where_clause:
                query += f" WHERE {where_clause}"
            if test_only_mode:
                query += ' ORDER BY date_added_in_db DESC LIMIT 3000'
            try:
                cursor.execute(query)
                rows = cursor.fetchall()
                cursor.close()
            except sqlite3.OperationalError as error:
                self.logger.warning(f"Error while getting assets data: {error!r}")
        return rows

    def get_columns_name_for_csv(self) -> list:
        """
        Get the columns name from the 'assets' table in a "CSV file" like format.
        :return: list (column_names).
        """
        csv_column_names = []
        if self.connection is not None:
            cursor = self.connection.cursor()
            # generate column names for the CSV file using AS to rename the columns
            fields = get_sql_field_name_list(exclude_csv_only=True, return_as_string=True, add_alias=True)
            query = f"SELECT {fields} FROM assets ORDER BY date_added_in_db DESC LIMIT 1"
            try:
                cursor.execute(query)
                csv_column_names = [
                    description[0] for description in cursor.description
                ]  # by using the 'AS' in the SQL query, the column names are the CSV column names
                cursor.close()
            except sqlite3.OperationalError as error:
                self.logger.warning(f"Error while getting columns name: {error!r}")
        return csv_column_names

    def create_empty_row(self, return_as_string=True, empty_cell='None', empty_row_prefix='dummy_row_'):
        """
        Create an empty row in the 'assets' table.
        :param return_as_string: True to return the row as a string, False to.
        :param empty_cell: The value to use for empty cells.
        :param empty_row_prefix: The prefix to use for the row ID.
        :return: A row (dict) or a string representing the empty row.
        """
        result = '' if return_as_string else {}
        # add a new row to the 'assets' table
        if self.connection is not None:
            cursor = self.connection.cursor()
            # generate a unique ID and check if it already exists in the database
            uid = ''
            count = 1
            while count > 0:
                uid = create_uid()
                cursor.execute("SELECT COUNT(*) FROM assets WHERE id = ?", (uid, ))
                count = cursor.fetchone()[0]
            cursor.close()
            ue_asset = UEAsset()
            ue_asset.data['asset_id'] = empty_row_prefix + uid  # dummy unique Asset_id to avoid issue
            ue_asset.data['thumbnail_url'] = empty_cell  # avoid displaying image warning on mouse over
            ue_asset.data['added_manually'] = True
            ue_asset.data['id'] = uid
            self.save_ue_asset(ue_asset)
            if return_as_string:
                result = str(ue_asset)
            else:
                # we read the new row from the database to get CSV column names
                result = self.get_assets_data_for_csv(where_clause=f"id = '{uid}'")
        return result

    def read_ue_asset(self, uid: str) -> UEAsset:
        """
        Read an UEAsset object from the 'assets' table.
        :param uid: The ID of the asset to get.
        :return: UEAsset object.
        """
        ue_asset = None
        if self.connection is not None:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * assets WHERE id = ?", (uid, ))
            row = cursor.fetchone()
            cursor.close()
            ue_asset = UEAsset()
            ue_asset.init_from_list(data=row)
        return ue_asset

    def save_ue_asset(self, ue_asset: UEAsset) -> None:
        """
        Save an UEAsset object to the 'assets' table.
        :param ue_asset: UEAsset object to save.
        """
        self.set_assets([ue_asset.data])

    def delete_asset(self, uid: str = '', asset_id: str = '') -> None:
        """
        Delete an asset from the 'assets' table by its ID or asset_id.
        :param uid: The ID of the asset to delete.
        :param asset_id: The Asset_id of the asset to delete. If both uid and asset_id are provided, only asset_id is used.
        """
        if self.connection is not None and (uid or asset_id):
            cursor = self.connection.cursor()
            if not asset_id:
                cursor.execute("DELETE FROM assets WHERE id = ?", (uid, ))
            else:
                cursor.execute("DELETE FROM assets WHERE asset_id = ?", (asset_id, ))
            self.connection.commit()
            cursor.close()

    def delete_all_assets(self, keep_added_manually=True) -> None:
        """
        Delete all assets from the 'assets' table.
        :param keep_added_manually: True to keep the assets added manually, False to delete all assets.
        """
        if keep_added_manually:
            where_clause = "added_manually = 0"
        else:
            where_clause = "1"
        if self.connection is not None:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM assets WHERE ?", (where_clause, ))
            self.connection.commit()
            cursor.close()

    def update_asset(self, column: str, value, uid: str = '', asset_id: str = '') -> None:
        """
        Update a specific column of an asset in the 'assets' table by its ID.
        :param column: The name of the column.
        :param value: The new value.
        :param uid: The ID of the asset to delete.
        :param asset_id: The Asset_id of the asset to delete. If both uid and asset_id are provided, only asset_id is used.
        """
        if self.connection is not None and (uid or asset_id):
            cursor = self.connection.cursor()
            if not asset_id:
                cursor.execute(f"UPDATE assets SET {column} = ? WHERE id = ?", (value, uid))
            else:
                cursor.execute(f"UPDATE assets SET {column} = ? WHERE asset_id = ?", (value, asset_id))
            self.connection.commit()
            cursor.close()

    # noinspection DuplicatedCode
    def save_tag(self, data: dict):
        """
        Save a tag into the 'tag' table.
        :param data: A dictionary containing the data to save.
        """
        # check if the database version is compatible with the current method
        if not self._check_db_version(DbVersionNum.V7, caller_name=inspect.currentframe().f_code.co_name):
            return
        if data.get('id', None) is None or data.get('name', None) is None:
            return
        if self.get_tag_by_id(data['id']) is None:
            cursor = self.connection.cursor()
            query = "INSERT INTO tags (id, name) VALUES (:id, :name)"
            cursor.execute(query, data)
            cursor.close()
            self.connection.commit()

    def get_tag_by_id(self, uid: int) -> str:
        """
        Read a tag name using its id from the 'tags' table.
        :param uid: The ID of the tag to get.
        :return: name of the tag.
        """
        result = None
        if self.connection is not None:
            cursor = self.connection.cursor()
            cursor.execute("SELECT name from tags WHERE id = ?", (uid, ))
            row = cursor.fetchone()
            cursor.close()
            result = row['name'] if row else result
        return result

    # noinspection DuplicatedCode
    def save_rating(self, data: dict):
        """
        Save a tag into the 'rating' table.
        :param data: A dictionary containing the data to save.
        """
        # check if the database version is compatible with the current method
        if not self._check_db_version(DbVersionNum.V8, caller_name=inspect.currentframe().f_code.co_name):
            return
        if data.get('id', None) is None or data.get('averageRating', None) is None:
            return
        if self.get_rating_by_id(data['id']) is None:
            cursor = self.connection.cursor()
            query = "INSERT INTO ratings (id, averageRating, total) VALUES (:id, :averageRating, :total)"
            cursor.execute(query, data)
            cursor.close()
            self.connection.commit()

    def get_rating_by_id(self, uid: int) -> ():
        """
        Read a rating using its id from the 'ratings' table.
        :param uid: The ID of the ratings to get.
        :return: tuple (averageRating, total)
        """
        result = (None, None)
        if self.connection is not None:
            cursor = self.connection.cursor()
            cursor.execute("SELECT averageRating, total from ratings WHERE id = ?", (uid, ))
            row = cursor.fetchone()
            cursor.close()
            result = (row['averageRating'], row['total']) if row else result
        return result

    def get_rows_with_tags_to_convert(self, tag_value: int = None) -> list:
        """
        Get all rows from the 'assets_tags' table that could be scrapped to fix their tags.
        :param tag_value: If not None, only get the rows that have a tag == tag_value.
        :return: A list of asset_id.
        Note: if tag_value is None, the returned list contains the asset_id that have at least a tag in the tags field that is an id in the tag table
        """
        rows = []
        if self.connection is not None:
            cursor = self.connection.cursor()
            if tag_value is None:
                # get the asset_id that have at least a tag in the tags field that is an id in the tag table
                cursor.execute("SELECT DISTINCT asset_id FROM assets_tags WHERE tag GLOB '*[^0-9]*' = 0 AND tag IN (SELECT id FROM tags)")
            else:
                # get the asset_id that have at least a tag in the tags field that is id == tag_value
                cursor.execute("SELECT asset_id FROM assets_tags WHERE CAST(tag AS INTEGER) == ?", tag_value)
            rows = cursor.fetchall()
            cursor.close()
        return [row[0] for row in rows]

    def convert_tag_list_to_string(self, tags: None) -> str:
        """
        Convert a tags id list to a comma separated string of tag names.
        """
        tags_str = ''
        if tags is not None and tags != [] and tags != {} and tags != '':
            if isinstance(tags, str):
                # noinspection PyBroadException
                try:
                    tags = tags.split(',')  # convert the string to a list
                except Exception:
                    return tags_str
            names = []
            for item in tags:
                if isinstance(item, int):
                    # temp: use the tag id as a name
                    name = self.get_tag_by_id(uid=item)
                    if name is None:
                        name = str(item)
                elif isinstance(item, dict):
                    uid = item.get('id', None)  # not used for now
                    name = item.get('name', '').title()
                    self.save_tag({'id': uid, 'name': name})
                else:
                    name = str(item).title()  # convert to string and capitalize
                if name and name not in names:
                    names.append(name)
            tags_str = ','.join(names)
        return tags_str

    def drop_tables(self) -> None:
        """
        Drop the 'assets' and 'last_run' tables.
        """
        if self.connection is not None:
            cursor = self.connection.cursor()
            cursor.execute("DROP TABLE IF EXISTS assets")
            cursor.execute("DROP TABLE IF EXISTS last_run")
            cursor.execute("DROP TABLE IF EXISTS tags")
            self.connection.commit()
            cursor.close()

    def generate_test_data(self, number_of_rows=1) -> None:
        """
        Generate and insert the specified number of fake assets into the 'assets' table.
        :param number_of_rows: The number of fake assets to generate and insert.
        """
        # check if the database version is compatible with the current method
        if not self._check_db_version(DbVersionNum.V2, caller_name=inspect.currentframe().f_code.co_name):
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
                random.choice([0, 1]),  # added_manually
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
                [fake.word(), fake.word(), fake.word()],  # tags
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
            'scraped_ids': ','.join(scraped_ids)
        }
        self.save_last_run(content)


if __name__ == "__main__":
    # the following code is just for class testing purposes
    clean_data = True
    read_data_only = True  # if True, the code will not create fake assets, but only read them from the database

    db_folder = path_from_relative_to_absolute('../../../scraping/')
    db_name = os.path.join(db_folder, 'assets.db')
    check_and_create_path(db_name)
    asset_handler = UEAssetDbHandler(database_name=db_name, reset_database=(clean_data and not read_data_only))

    if read_data_only:
        # Read existing assets
        asset_list = asset_handler.get_assets_data()
        print("Assets:", asset_list)
    elif test_only_mode:
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
