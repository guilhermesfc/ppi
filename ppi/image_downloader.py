import requests
import os
import shutil
from ppi.database import Database, DBAction, DBActionStatus
from loguru import logger

"""Class for downloading images into disk"""


class ImageDownloader:
    """Downloads images from a database with urls to disk.

    Attributes:
        config: The configuration for the image downloader.
        database: The database to download images from.
    """

    def __init__(self, config: dict, database: Database) -> None:
        self.config = config
        self.database = database

    def _download_url(self, url: str, path: str) -> None:
        """Downloads an image from the given URL to the given path.

        Args:
            url: The URL of the image to download.
            path: The path to save the image to.
        """
        try:
            response = requests.get(url)
            ext = url.split(".")[-1]
            with open(f"{path}.{ext}", "wb") as file:
                file.write(response.content)
        except Exception as e:
            logger.error(
                f"An exception {str(e)} of type {type(e).__name__} occurred while downloading image {url}."
            )

    def download_images(self, max_number_downloads: int = 250) -> None:
        """Downloads all images in the database to disk.

        Args:
            max_number_downloads: The maximum number of images to download.
        """
        for medium in self.config["allowed_processes"]:
            logger.info(f"Downloading images for medium {medium}")
            download_dir = os.path.join(self.config["dir"]["download"], medium)
            os.makedirs(download_dir, exist_ok=True)
            result = self.database.get_next_image_download(medium)
            i = 0
            while result:
                source, id, url = result
                if i <= max_number_downloads:
                    file_path = os.path.join(download_dir, f"{source}_{id}")
                    logger.info(f"Downloading: {url}")
                    try:
                        self._download_url(url=url, path=file_path)
                        self.database.write_log(
                            "", DBAction.DOWNLOAD, DBActionStatus.SUCCESS, url
                        )
                        i += 1
                    except Exception as e:
                        logger.error(
                            f"An exception {str(e)} of type {type(e).__name__} occurred while downloading image {url}."
                        )
                        self.database.write_log(
                            "", DBAction.DOWNLOAD, DBActionStatus.SUCCESS, url
                        )
                    result = self.database.get_next_image_download(medium)
                else:
                    break
            logger.info(
                "No more images to download"
                if i < max_number_downloads
                else "Maximum number of images downloaded"
            )
        logger.info("Backing up images")
        backup_dir = os.path.join(self.config["dir"]["backup"])
        os.makedirs(backup_dir, exist_ok=True)
        for medium in self.config["allowed_processes"]:
            download_dir = os.path.join(self.config["dir"]["download"], medium)
            for file in os.listdir(download_dir):
                source_file_path = os.path.join(download_dir, file)
                destination_file_path = os.path.join(self.config["dir"]["backup"], file)
                if not os.path.exists(destination_file_path):
                    shutil.copy(source_file_path, destination_file_path)
        logger.info("Back up completed")
