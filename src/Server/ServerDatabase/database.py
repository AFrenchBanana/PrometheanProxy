import sqlite3

class DatabaseClass:
    """class that handles the database within the project"""

    def __init__(self, config) -> None:
        self.config = config
        self.create_db_connection()
        self.initalise_database()

    def create_db_connection(self) -> None:
        try:
            self.dbconnection = sqlite3.connect(f"{self.config['database']['file']}")
            self.cursor = self.dbconnection.cursor()
        except sqlite3.Error as err:
            print("Database connection failed")
            print(err)
            self.cursor = None
        return

    def initalise_database(self) -> None:
        if not self.cursor:
            print("Database cursor is not available.")
            return

        for table in self.config['tables']:
            try:
                table_query = (
                    "CREATE TABLE IF NOT EXISTS "
                    f"{table['name']}({table['schema']})"
                )
                self.cursor.execute(table_query)
                self.dbconnection.commit()
            except sqlite3.Error as err:
                print("Failed to create table:", table['name'])
                print(err)