from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine.result import Result
import pandas as pd
import datetime as dt
from enum import Enum
from typing import List, Tuple
from typing import Union, Literal
from loguru import logger

"""Classes for interacting with SQLite Database"""


class DBAction(Enum):
    """An enumeration of all actions recorded on the database."""

    IMAGE_PROCESS = "image process"
    PAGE_PROCESS = "page process"
    DOWNLOAD = "download"


class DBActionStatus(Enum):
    """An enumeration of the status of all actions recorded on the database."""

    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


class Database:
    """A database class for storing and retrieving image metadata.

    Attributes:
        engine: A SQLAlchemy engine.
    """

    def __init__(self, db_name: str) -> None:
        """Initializes a new SQLite engine.

        Args:
            db_name: The name of the database file.

        Returns:
            None.
        """
        self.engine = create_engine("sqlite:///" + db_name)

    def _execute_query(self, query: str) -> Result:
        """Executes a SQL query.

        Args:
            query: The SQL query to execute.
            params: A dictionary of parameters to pass to the query.

        Returns:
            The results of the query, or `False` if there is an OperationalError.
        """
        connection = self.engine.connect()
        try:
            result = connection.execute(text(query))
            return result
        except Exception as e:
            logger.error(
                f"An exception {str(e)} of type {type(e).__name__} occurred while executing query {query}."
            )
            raise e
        finally:
            connection.close()

    def save_data(
        self,
        data: pd.DataFrame,
        table: str,
        if_exists: Literal["fail", "replace", "append"] = "append",
    ) -> None:
        """Saves data into the database.

        Args:
            data: A Pandas DataFrame containing the data to save.
            table: The name of the table to save the data to.
            if_exists: The behavior if the table already exists. Possible values:
                * "append": Append the data to the existing table.
                * "replace": Replace the existing table with the new data.
                * "fail": Raise an exception if the table already exists.
            Defaults to "append".

        Returns:
            None.
        """
        data.to_sql(table, con=self.engine, if_exists=if_exists, index=False)

    def write_log(
        self, source: str, action: DBAction, status: DBActionStatus, url: str
    ) -> None:
        """Writes a log entry to the database.

        Args:
            source: The source of the log entry.
            action: The action that was performed.
            status: The status of the action.
            url: The URL that the action was performed on.

        Returns:
            None.
        """
        self.save_data(
            pd.DataFrame(
                {
                    "source": source,
                    "action": [action.value],
                    "status": status.value,
                    "url": [url],
                    "date": [dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S")],
                }
            ),
            "log",
        )

    def check_log(self, action: DBAction, url: str) -> bool:
        """Checks whether an entry exists in the log for the given action and URL.

        Args:
            action: The action to check for.
            url: The URL to check for.

        Returns:
            True if an entry exists in the log for the given action and URL, False otherwise.
        """
        inspector = inspect(self.engine)
        if inspector.has_table("log"):  # Check if table already exists
            query = (
                "select count(*) FROM log where url = '"
                + url.replace("'", "''")
                + "' and action = '"
                + action.value
                + "'"
            )
            result = self._execute_query(query).fetchone()
            if result and result[0] > 0:
                return True
        return False

    def get_next_image_download(
        self, medium: Union[str, None] = None
    ) -> Union[Tuple[str, str, str], None]:
        """Returns the data for the next image to download, based on the given medium.
        If no medium is given, the next image to download will be selected from all images.

        Args:
            medium: The medium to filter the images by.

        Returns:
            A tuple containing the source, ID, and URL of the next image to download, or None if there are no more images to download.
        """
        if medium:
            query = (
                "select img.source,img.id,img.url FROM images as img inner join mediums as me on img.id = me.id where img.url not in (select distinct url from log where action = 'download') and me.new_medium = '"
                + medium
                + "'"
            )
        else:
            query = "select source,id,url FROM images where url not in (select distinct url from log where action = 'download')"
        result = self._execute_query(query).fetchone()
        if result:
            source, img, url = result
            return source, img, url
        else:
            return None

    def get_medium(self, source: str, id: str) -> Union[str, None]:
        """Returns the medium for the given source and ID.

        Args:
            source: The source of the image.
            id: The ID of the image.

        Returns:
            The medium for the image.
        """
        query = (
            "select new_medium FROM mediums where source='"
            + source
            + "' and id='"
            + id
            + "'"
        )
        result = self._execute_query(query).fetchone()
        if result is not None:
            new_medium = result[0]
            return new_medium
        else:
            return None

    def get_images_to_update(self) -> Union[List[Tuple[str, str, str]], None]:
        """Returns a list of all images that need to be updated, along with their source, ID, and medium.

        Returns:
            A list of tuples, where each tuple contains the following data:
                * Source
                * ID
                * Medium
        """
        query = "select source, id, medium FROM images"
        result = self._execute_query(query).fetchall()
        if result:
            images_to_update: List[Tuple[str, str, str]] = [
                (entry[0], entry[1], entry[2]) for entry in result
            ]
            return images_to_update
        else:
            return None

    def get_all_mediums(self) -> Union[List[str], None]:
        """Returns a list of all unique mediums in the database.

        Returns:
            A list of tuples, where each tuple contains a medium.
        """
        query = "select distinct medium FROM images"
        result = self._execute_query(query).fetchall()
        if result:
            mediums: List[str] = [entry[0] for entry in result]
            return mediums
        else:
            return None

    def get_all_mediums_count(self) -> Union[List[Tuple[str, int]], None]:
        """Returns a list of all unique mediums in the database, along with the number of images associated with each medium.

        Returns:
            A list of tuples, where each tuple contains the following data:

                * Medium
                * Count
        """
        query = "select distinct medium, count(*) FROM images group by medium"
        result = self._execute_query(query).fetchall()
        if result:
            mediums_count: List[Tuple[str, int]] = [
                (entry[0], entry[1]) for entry in result
            ]
            return mediums_count
        else:
            return None
