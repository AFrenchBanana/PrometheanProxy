#!/usr/bin/python3
import sqlite3
from Modules.global_objects import config


class DatabaseClass:
    """class that handles the database within the project"""

    def __init__(self) -> None:
        self.create_db_connection()
        self.initalise_database()

    def create_db_connection(self) -> None:
        """attempts to create a connection to a database and then
        calls the initialise_database function.
        Function needs the path to the db file to use."""
        try:
            self.dbconnection = (
                sqlite3.connect(f"{config['database']['file']}"))
            self.cursor = self.dbconnection.cursor()
        except sqlite3.Error as err:
            print("Database connection failed")
            print(err)
            self.cursor = None  # Ensure cursor is None if connection fails
        return

    def initalise_database(self) -> None:
        """
        Attempts to create the required database tables for the
        database to function properly.
        """
        if not self.cursor:
            print("Database cursor is not available.")
            return

        for table in config['tables']:  # load tables as in config file
            try:
                table_query = (
                    "CREATE TABLE IF NOT EXISTS " +
                    f"{table['name']}({table['schema']})")
                self.cursor.execute(table_query)
                self.dbconnection.commit()  # commits the table creation
            except sqlite3.Error as err:
                print(f"Error creating table {table['name']}: {err}")
                continue
        return

    def insert_entry(self, table: str, values: tuple) -> None:
        """SQL Query to insert data into a table.
        Example: insert_entry('Connections', (123, 'data'))"""
        if not self.cursor:
            print("Database cursor is not available.")
            return

        if config['database']['addData']:
            try:
                table_query = f"INSERT INTO {table} VALUES ({values})"
                self.cursor.execute(table_query)
                self.dbconnection.commit()  # commits the data
            except sqlite3.Error as err:
                if not config["server"]["quiet_mode"]:
                    print(f"Error inserting into table {table}: {err}")
        return

    def search_query(self, selectval: str, table: str,
                     column: str, value: str) -> str:
        """Search query for database searching"""
        if not self.cursor:
            print("Database cursor is not available.")
            return None

        try:
            query = f"SELECT {selectval} FROM {table} WHERE {column} = ?"
            self.cursor.execute(query, (value,))
            return self.cursor.fetchone()  # return the first matched result
        except sqlite3.Error as err:
            print(f"Error executing search query: {err}")
            return None
