# coding=utf-8
"""
implementation for:
- DatabaseConnection: Context manager for opening and closing a database connection.
- UEAssetDbHandler: Handles database operations for the UE Assets.
"""
import os
import sqlite3
from faker import Faker
import random
from typing import List, Dict


class DatabaseConnection:
    """
    Context manager for opening and closing a database connection.
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
    :param ldb_name: The name of the database file.
    """

    def __init__(self, ldb_name: str):
        self.db_name = ldb_name

    def db_exists(self) -> bool:
        """
        Check if the database file exists.

        :return: True if the database file exists, otherwise False.
        """
        return os.path.exists(self.db_name)

    def create_table(self) -> None:
        """
          Create the 'assets' table if it doesn't exist.
          """

        with DatabaseConnection(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'CREATE TABLE IF NOT EXISTS assets ( id TEXT PRIMARY KEY, namespace TEXT, catalog_item_id TEXT, title TEXT, category TEXT, author TEXT, thumbnail_url TEXT, current_price_discounted REAL, asset_slug TEXT, currency_code TEXT, description TEXT, technical_details TEXT, long_description TEXT, categories TEXT, tags TEXT, comment_rating_id TEXT, rating_id TEXT, status TEXT, price REAL, discount REAL, discount_price REAL, discount_percentage REAL, is_featured BOOL, is_catalog_item BOOL, is_new BOOL, free BOOL, discounted BOOL, can_purchase BOOL, owned INTEGER, review REAL, review_count INTEGER, Comment TEXT, Stars INTEGER, Must_buy BOOL, Test_result TEXT, Installed_folder TEXT, Alternative TEXT, Origin TEXT'
            )
            conn.commit()

    def update_table_structure(self) -> None:
        """
          Get all assets from the 'assets' table.

          :return: A list of dictionaries representing assets.
          """
        with DatabaseConnection(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(assets)")

            columns = {row[1]: row for row in cursor.fetchall()}

            required_columns = {
                'Comment': 'TEXT',
                'Stars': 'INTEGER',
                'Must_buy': 'BOOL',
                'Test_result': 'TEXT',
                'Installed_folder': 'TEXT',
                'Alternative': 'TEXT',
                'Origin': 'TEXT'
            }

            for column_name, data_type in required_columns.items():
                if column_name not in columns:
                    cursor.execute(f"ALTER TABLE assets ADD COLUMN {column_name} {data_type}")

            conn.commit()

    def get_row_count(self) -> int:
        """
        Get the number of rows in the 'assets' table.
        :return:  The number of rows in the 'assets' table.
        """
        with DatabaseConnection(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM assets")

            row_count = cursor.fetchone()[0]

        return row_count

    def insert_assets(self, assets) -> None:
        """
        Insert assets into the 'assets' table.
        :param assets: A dictionary or a list of dictionaries representing assets.
        """
        with DatabaseConnection(self.db_name) as conn:
            cursor = conn.cursor()
            if not isinstance(assets, list):
                assets = [assets]

            for asset in assets:
                cursor.execute(
                    'INSERT OR REPLACE INTO assets (id, namespace, catalog_item_id, title, category, author, thumbnail_url, current_price_discounted, asset_slug, currency_code, description, technical_details, long_description, categories, tags, comment_rating_id, rating_id, status, price, discount, discount_price, discount_percentage, is_featured, is_catalog_item, is_new, free, discounted, can_purchase, owned, review, review_count, Comment, Stars, Must_buy, Test_result, Installed_folder, Alternative, Origin) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (
                        asset['id'], asset['namespace'], asset['catalog_item_id'], asset['title'], asset["category"], asset['author'],
                        asset['thumbnail_url'], asset['current_price_discounted'], asset['asset_slug'], asset['currency_code'], asset['description'],
                        asset['technical_details'], asset['long_description'], str(asset['categories']), str(asset['tags']),
                        asset['comment_rating_id'], asset['rating_id'], asset['status'], asset['price'], asset['discount'], asset['discount_price'],
                        asset['discount_percentage'], asset['is_featured'], asset['is_catalog_item'], asset['is_new'], asset['free'],
                        asset['discounted'], asset['can_purchase'], asset['owned'], asset['review'], asset['review_count'], asset['Comment'],
                        asset['Stars'], asset['Must_buy'], asset['Test_result'], asset['Installed_folder'], asset['Alternative'], asset['Origin']
                    )
                )

            conn.commit()

    def get_assets(self) -> List[Dict]:
        """
        Get all assets from the 'assets' table.

        :return: A list of dictionaries representing assets.
        """

        with DatabaseConnection(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM assets")

            assets = [
                {
                    'id': row[0],
                    'namespace': row[1],
                    'catalog_item_id': row[2],
                    'title': row[3],
                    'category': row[4],
                    'author': row[6],
                    'thumbnail_url': row[7],
                    'current_price_discounted': row[8],
                    'asset_slug': row[9],
                    'currency_code': row[10],
                    'description': row[11],
                    'technical_details': row[12],
                    'long_description': row[13],
                    'categories': row[14],
                    'tags': row[15],
                    'comment_rating_id': row[16],
                    'rating_id': row[17],
                    'status': row[18],
                    'price': row[19],
                    'discount': row[20],
                    'discount_price': row[21],
                    'discount_percentage': row[22],
                    'is_featured': row[23],
                    'is_catalog_item': row[24],
                    'is_new': row[25],
                    'free': row[26],
                    'discounted': row[27],
                    'can_purchase': row[28],
                    'owned': row[29],
                    'review': row[30],
                    'review_count': row[31],
                    'Comment': row[32],
                    'Stars': row[33],
                    'Must_buy': row[34],
                    'Test_result': row[35],
                    'Installed_folder': row[36],
                    'Alternative': row[37],
                    'Origin': row[38]
                } for row in cursor.fetchall()
            ]

        return assets

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
        :param column: The name of the column to update.
        :param value: The new value for the specified column.
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
        fake = Faker()

        for index in range(number_of_rows):
            assets_id = fake.uuid4()
            print(f'creating test asset # {index} with id {assets_id}')

            sample_assets = {
                'id': assets_id,
                'namespace': fake.word(),
                'catalog_item_id': fake.uuid4(),
                'title': fake.sentence(),
                'category': fake.word(),
                'author': fake.name(),
                'thumbnail_url': fake.image_url(),
                'current_price_discounted': round(random.uniform(1, 100), 2),
                'asset_slug': fake.slug(),
                'currency_code': 'USD',
                'description': fake.text(),
                'technical_details': fake.text(),
                'long_description': fake.text(),
                'categories': [{
                    'name': fake.word()
                }],
                'tags': [fake.word(), fake.word()],
                'comment_rating_id': fake.uuid4(),
                'rating_id': fake.uuid4(),
                'status': fake.word(),
                'price': round(random.uniform(1, 100), 2),
                'discount': round(random.uniform(1, 100), 2),
                'discount_price': round(random.uniform(1, 100), 2),
                'discount_percentage': round(random.uniform(0, 100), 2),
                'is_featured': random.choice([0, 1]),
                'is_catalog_item': random.choice([0, 1]),
                'is_new': random.choice([0, 1]),
                'free': random.choice([0, 1]),
                'discounted': random.choice([0, 1]),
                'can_purchase': random.choice([0, 1]),
                'owned': random.choice([0, 1]),
                'review': round(random.uniform(0, 5), 1),
                'review_count': random.randint(0, 1000),
                'Comment': fake.text(),
                'Stars': random.randint(1, 5),
                'Must_buy': random.choice([0, 1]),
                'Test_result': fake.word(),
                'Installed_folder': fake.file_path(),
                'Alternative': fake.sentence(),
                'Origin': fake.word()
            }

            self.insert_assets(sample_assets)


if __name__ == "__main__":
    db_name = "assets.db"
    asset_handler = UEAssetDbHandler(db_name)

    if not asset_handler.db_exists():
        asset_handler.create_table()

    asset_handler.update_table_structure()

    rows_count = asset_handler.get_row_count()
    print(f"Rows count: {rows_count}")
    rows_to_create = 5000 - rows_count
    print(f"Creating {rows_to_create} rows")
    asset_handler.generate_test_data(rows_to_create)

    # Read assets
    asset_list = asset_handler.get_assets()
    print("Assets:", asset_list)

    # Example usage
    # fake = Faker()
    # id = fake.uuid4()
    # sample_assets = [
    #     {
    #         'id': id,
    #         'namespace': "namespace1",
    #         'catalog_item_id': "catalogItemId1",
    #         'title': "title1",
    #         'category': "category1",
    #         'category_slug': "categorySlug1",
    #         'author': "author1",
    #         'thumbnail_url': "thumbnailUrl1",
    #         'current_price_discounted': 10.0,
    #         'asset_slug': "assetSlug1",
    #         'currency_code': "USD",
    #         'description': "description1",
    #         'technical_details': "technicalDetails1",
    #         'long_description': "longDescription1",
    #         'categories': [{
    #             'name': 'category1'
    #         }],
    #         'tags': ['tag1', 'tag2'],
    #         'comment_rating_id': "commentRatingId1",
    #         'rating_id': "ratingId1",
    #         'status': "status1",
    #         'price': 25.0,
    #         'discount': 15.0,
    #         'discount_price': 10.0,
    #         'discount_percentage': 40.0,
    #         'is_featured': 1,
    #         'is_catalog_item': 1,
    #         'is_new': 1,
    #         'free': 0,
    #         'discounted': 1,
    #         'can_purchase': 1,
    #         'owned': 0,
    #         'review': 4.5,
    #         'review_count': 10,
    #         'Comment': "Great asset!",
    #         'Stars': 5,
    #         'Must_buy': 1,
    #         'Test_result': "Passed",
    #         'Installed_folder': "folder1",
    #         'Alternative': "alternative1",
    #         'Origin': "origin1"
    #     }
    # ]
    # asset_handler.insert_assets(sample_assets)

    # Update an asset
    # asset_handler.update_asset("1", "title", "Updated Title")

    # Delete an asset
    # asset_handler.delete_asset("1")

    # Verify deletion
    # assets = asset_handler.get_assets()
    # print("Assets after deletion:", assets)
