from datetime import datetime
from typing import Dict, Any
import logging
from pymongo import MongoClient, database

import setup 

setup.LoggerSetup()
logger = logging.getLogger()


class MongoDBHandler:
    """A class to handle interactions with MongoDB, creating and appending data to databases.
    
    Attributes:
        host (str): The MongoDB server host. 
        port (int): The MongoDB server port. 
    """

    def __init__(self, host: str = 'localhost', port: int = 27017) -> None:
        self.client = MongoClient(host, port)
        self.failed_books_db = self._get_or_create_database('failed_evidence_books')
        self.books_metadata_db = self._get_or_create_database('evidence_books_metadata')

    def _get_or_create_database(self, db_name: str) -> database.Database:
        """Get or create a MongoDB database.

        Args:
            db_name (str): The name of the database to get or create.

        Returns:
            database.Database: The MongoDB database object.
        """
        if db_name not in self.client.list_database_names():
            logger.info(f"Creating database: {db_name}")
        return self.client[db_name]

    def append_to_failed_books(self, book_id: str, reason: str) -> None:
        """Append data to the failed_books database.

        Args:
            book_id str: number of the evidence book.
            reason str: reason of failure. 
        """
        data = {'book_id': book_id, 'reason': reason}
        self._append_data(self.failed_books_db, data)

    def append_to_books_metadata(self, data: Dict[str, Any]) -> None:
        """Append data to the books_metadata database.

        Args:
            data (Dict[str, Any]): The books metadata to be appended.
        """
        self._append_data(self.books_metadata_db, data)

    def _append_data(self, db: database.Database, data: Dict[str, Any]) -> None:
        """Append data to a specified MongoDB database with an injection timestamp.

        Args:
            db (database.Database): The database to which the data should be appended.
            data (Dict[str, Any]): The data to append.
        """ 
        data['injection_timestamp'] = datetime.now()
        db['data'].insert_one(data)
        logger.info(f"Data appended to {db.name} at {data['injection_timestamp']}.")
    
    def get_last_book_by_department(self, department_code: str) -> int:
        """Retrieve last book code with a specific department code from the metadata database.

        Args:
            department_code (str): The department code to search for.

        Returns:
            int: a code of last book matching the department code.
        """
        books = self.books_metadata_db['data'].find({'id': {'$regex': f'^{department_code}/'}}, 
                                                    {'id': 1})
        
        return max([book['id'].split('/')[1] for book in books if '/' in book['id']], default = None)