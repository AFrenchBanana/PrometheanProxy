#!/usr/bin/python3
import sqlite3
from Modules.content_handler import TomlFiles
from Modules.global_objects import config

class DatabaseClass:
    """class that handles the database within the project"""
    def __init__(self) -> None:
        self.create_db_connection() #creates the db connection
        self.initalise_database() # intalises the DB


    def create_db_connection(self) -> None:
        """attempts to creates a connection to a database and then 
        calls the initialise_database function
        Function needs the path to the db file to use"""
        try:
            self.dbconnection = sqlite3.connect(f"{config['database']['file']}")  #connects to the database
            self.cursor = self.dbconnection.cursor()  # creates a database cursors
            
        except sqlite3.Error as err: # catch and print error
            print("Database connection failed")
            print(err)
        return

    def initalise_database(self) -> None:
        """attempts to create the required database tables for the database to function properly."""
        for tables in config['tables']: # load tables as in config file
            try:
                table_query = f"CREATE TABLE {tables['name']}({tables['schema']})" # sql query to make tables
                self.cursor.execute(table_query)
                self.dbconnection.commit() # commits the table
            except sqlite3.Error: 
                continue
        return   


    def insert_entry(self, table: str, values: tuple) -> None:
        """SQL Query to insert data into a table.
        Example: insert_entry(Connections, "123")"""
        if config['database']['addData'] == True:
            try:
                table_query = f"INSERT INTO {table} VALUES ({values})" # sql query to insert data
                self.cursor.execute(table_query) # executes the table query
                self.dbconnection.commit() #commits the data
            except:
                if not config["server"]["quiet_mode"]:
                    print("Error inserting into database")
        return
        

    def search_query(self, selectval: str, table: str, column: str, value: str) -> str:
        """search query for database seaching """
        search_value = (value, ) # sets the search value
        self.cursor.execute(f"SELECT {selectval} FROM {table} WHERE {column} = ?", (search_value)) # execute the search query 
        return self.cursor.fetchone() # return the answer
