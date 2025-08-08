import sqlite3
import os
from Modules.global_objects import logger


class DatabaseClass:
    """
    Class that handles the database within the project.
    This version is SQL injection-proof through whitelisting and parameterized queries.
    The table and column whitelists are now generated dynamically from the config.
    """

    def __init__(self, config) -> None:
        logger.debug("DatabaseClass: Initializing database connection")
        self.config = config

        # --- Dynamic Whitelists for SQL Injection Prevention ---
        # Instead of hardcoding, we now parse the allowed tables and columns
        # from the provided configuration.
        self._allowed_tables = {}
        self._allowed_columns_by_table = {}

        for table_config in self.config.get('tables', []):
            table_name = table_config['name']
            schema_str = table_config['schema']
            self._allowed_tables[table_name] = schema_str
            
            # Extract column names from the schema string for the whitelist
            columns = [
                part.strip().split(' ')[0]
                for part in schema_str.split(',')
            ]
            self._allowed_columns_by_table[table_name] = columns
        
        logger.debug(f"DatabaseClass: Generated _allowed_tables: {self._allowed_tables}")
        logger.debug(f"DatabaseClass: Generated _allowed_columns_by_table: {self._allowed_columns_by_table}")

        self.create_db_connection()
        self.initalise_database()

    def create_db_connection(self) -> None:
        """
        Attempts to create a connection to a database.
        """
        logger.debug("DatabaseClass: Creating database connection")
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
        Attempts to create the required database tables based on a
        whitelist generated from the config file.
        """
        logger.debug("DatabaseClass: Initializing database tables")
        if not self.cursor:
            logger.error("DatabaseClass: Database cursor is not available")
            print("Database cursor is not available.")
            return

        for table_name, schema in self._allowed_tables.items():
            try:
                # Table name and schema are from the trusted whitelist, not user input.
                table_query = f"CREATE TABLE IF NOT EXISTS {table_name}({schema})"
                self.cursor.execute(table_query)
                self.dbconnection.commit()  # commits the table creation
                logger.debug(f"DatabaseClass: Table {table_name} created successfully")
            except sqlite3.Error as err:
                print(f"Error creating table {table_name}: {err}")
                logger.error(f"DatabaseClass: Error creating table {table_name}: {err}")
                continue
        return

    def insert_entry(self, table: str, values: tuple) -> None:
        """
        SQL Query to insert data into a table.
        This version uses a whitelist for the table name and a parameterized query.
        """
        if not self.cursor:
            logger.error("DatabaseClass: Database cursor is not available")
            print("Database cursor is not available.")
            return

        # CRITICAL: Validate the table name against a whitelist.
        if table not in self._allowed_tables:
            logger.error(f"DatabaseClass: Unauthorized table insertion attempt: {table}")
            print(f"Error: Attempted to insert into an unauthorized table: {table}")
            return

        if self.config['database']['addData']:
            try:
                logger.debug(f"DatabaseClass: Inserting into table {table} values {values}")
                placeholders = ','.join(['?' for _ in values])
                # The table name is from the whitelist, but values are parameterized.
                table_query = f"INSERT INTO {table} VALUES ({placeholders})"
                self.cursor.execute(table_query, values)
                logger.debug(f"DatabaseClass: Query {table_query} with values {values}")
                self.dbconnection.commit()
            except sqlite3.Error as err:
                if not self.config["server"]["quiet_mode"]:
                    logger.error(f"DatabaseClass: Error inserting into table {table}: {err}")
                    print(f"Error inserting into table {table}: {err}")
        return

    def search_query(self, selectval: str, table: str,
                     column: str, value: str) -> str:
        """
        Search query for database searching, now with robust SQLi prevention.
        """
        logger.debug(f"DatabaseClass: Searching in table {table} for {column} = {value}")
        if not self.cursor:
            logger.error("DatabaseClass: Database cursor is not available")
            print("Database cursor is not available.")
            return None

        # CRITICAL: Whitelist validation for table, column, and selectval.
        if table not in self._allowed_tables:
            logger.error(f"DatabaseClass: Unauthorized table access attempt: {table}")
            print(f"Error: Attempted to query an unauthorized table: {table}")
            return None
        
        allowed_columns = self._allowed_columns_by_table.get(table)
        if allowed_columns is None:
            logger.error(f"DatabaseClass: No allowed columns defined for table: {table}")
            print(f"Error: No allowed columns defined for table: {table}")
            return None

        if column not in allowed_columns:
            logger.error(f"DatabaseClass: Unauthorized column access attempt: {column} in table {table}")
            print(f"Error: Unauthorized column access attempt: {column}")
            return None

        # Check if `selectval` is a single allowed column or the wildcard '*'.
        # This will also support multiple comma-separated columns from the whitelist.
        selected_columns = [col.strip() for col in selectval.split(',')]
        if selectval != '*' and not all(c in allowed_columns for c in selected_columns):
            logger.error(f"DatabaseClass: Unauthorized select value attempt: {selectval}")
            print(f"Error: Unauthorized select value attempt: {selectval}")
            return None
        
        try:
            query = f"SELECT {selectval} FROM {table} WHERE {column} = ?"
            logger.debug(f"DatabaseClass: Executing query: {query} with value {value}")
            self.cursor.execute(query, (value,))
            return self.cursor.fetchone()  # return the first matched result
        except sqlite3.Error as err:
            if not self.config["server"]["quiet_mode"]:
                print(f"Error executing search query: {err}")
            return None
