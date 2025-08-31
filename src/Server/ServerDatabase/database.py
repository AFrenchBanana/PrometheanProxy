import sqlite3
import os
from Modules.global_objects import logger


class DatabaseClass:
    def _safe_identifier(self, identifier, valid_list):
        """Ensure identifier (table/column) is valid and whitelisted."""
        if identifier in valid_list:
            return identifier
        raise ValueError(f"Invalid identifier: {identifier}")

    """class that handles the database within the project"""

    def __init__(self, config) -> None:
        logger.debug("DatabaseClass: Initializing database connection")
        self.config = config
        self.create_db_connection()
        self.initalise_database()

    def create_db_connection(self) -> None:
        logger.debug("DatabaseClass: Creating database connection")
        """attempts to create a connection to a database and then
        calls the initialise_database function.
        Function needs the path to the db file to use."""
        try:
            dbPath = os.path.expanduser(f"{self.config['database']['file']}")
            if not os.path.exists(dbPath):
                logger.debug(f"DatabaseClass: Database file {dbPath} does not exist, creating it")
                os.makedirs(os.path.dirname(dbPath), exist_ok=True)
            self.dbconnection = sqlite3.connect(
                dbPath,
                check_same_thread=False)
            self.cursor = self.dbconnection.cursor()
            logger.debug("DatabaseClass: Database connection established")
        except sqlite3.Error as err:
            logger.error("DatabaseClass: Database connection failed")
            print("Database connection failed")
            print(err)
            self.cursor = None  # Ensure cursor is None if connection fails
        return

    def initalise_database(self) -> None:
        """
        Attempts to create the required database tables for the
        database to function properly.
        """
        logger.debug("DatabaseClass: Initializing database tables")
        if not self.cursor:
            logger.error("DatabaseClass: Database cursor is not available")
            print("Database cursor is not available.")
            return

        for table in self.config['tables']:  # load tables as in self.config file
            try:
                table_query = (
                    "CREATE TABLE IF NOT EXISTS " +
                    f"{table['name']}({table['schema']})")
                self.cursor.execute(table_query)
                self.dbconnection.commit()  # commits the table creation
                logger.debug(f"DatabaseClass: Table {table['name']} created successfully")
            except sqlite3.Error as err:
                print(f"Error creating table {table['name']}: {err}")
                logger.error(f"DatabaseClass: Error creating table {table['name']}: {err}")
                continue
        return

    def insert_entry(self, table: str, values: tuple) -> None:
        """SQL Query to insert data into a table using parameterized queries."""
        if not self.cursor:
            logger.error("DatabaseClass: Database cursor is not available")
            print("Database cursor is not available.")
            return

        # Validate table name
        valid_tables = [t['name'] for t in self.config['tables']]
        try:
            safe_table = self._safe_identifier(table, valid_tables)
        except ValueError as err:
            logger.error(f"DatabaseClass: {err}")
            print(err)
            return

        if self.config['database']['addData']:
            try:
                logger.debug(f"DatabaseClass: Inserting into table {safe_table} values {values}")
                placeholders = ','.join(['?'] * len(values))
                table_query = f"INSERT INTO {safe_table} VALUES ({placeholders})"
                self.cursor.execute(table_query, values)
                logger.debug(f"DatabaseClass: Query {table_query} with values {values}")
                self.dbconnection.commit()  # commits the data
            except sqlite3.Error as err:
                if not self.config["server"]["quiet_mode"]:
                    logger.error(f"DatabaseClass: Error inserting into table {safe_table}: {err}")
                    print(f"Error inserting into table {safe_table}: {err}")
        return

    def search_query(self, selectval: str, table: str,
                     column: str, value: str) -> str:
        """Search query for database searching using parameterized queries and identifier validation."""
        logger.debug(f"DatabaseClass: Searching in table {table} for {column} = {value}")
        if not self.cursor:
            logger.error("DatabaseClass: Database cursor is not available")
            print("Database cursor is not available.")
            return None

        # Validate table and column names
        valid_tables = [t['name'] for t in self.config['tables']]
        try:
            safe_table = self._safe_identifier(table, valid_tables)
            # Find the table schema and get valid columns
            table_schema = next((t['schema'] for t in self.config['tables'] if t['name'] == safe_table), None)
            if not table_schema:
                raise ValueError(f"No schema found for table {safe_table}")
            # Extract column names from schema string (format: 'id INTEGER PRIMARY KEY, name TEXT, ...')
            valid_columns = [col.split()[0] for col in table_schema.split(',')]
            safe_column = self._safe_identifier(column, valid_columns)
        except ValueError as err:
            logger.error(f"DatabaseClass: {err}")
            print(err)
            return None

        try:
            query = f"SELECT {selectval} FROM {safe_table} WHERE {safe_column} = ?"
            logger.debug(f"DatabaseClass: Executing query: {query} with value {value}")
            self.cursor.execute(query, (value,))
            return self.cursor.fetchone()  # return the first matched result
        except sqlite3.Error as err:
            print(f"Error executing search query: {err}")
            logger.error(f"DatabaseClass: Error executing search query: {err}")
            return None
