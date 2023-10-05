import requests
from bs4 import BeautifulSoup
from abc import ABC, abstractmethod
import time
from loguru import logger
import pandas as pd
import re
from ppi.database import Database
from typing import List
from ppi.database import DBAction, DBActionStatus


"""Classes for crawling the web for image metadata"""


class ImageMetadataCrawler(ABC):
    """An abstract class for crawling image metadata from the web.

    Attributes:
        config: The configuration data.
        database: The database to store the extracted image metadata in.
        regex_for_image_links: A regular expression to match image URLs.
        medium: The medium of the images to crawl.
    """

    def __init__(
        self, config: dict, database: Database, regex_for_image_links: str
    ) -> None:
        """Extracts image metadata from the given URL.

        Args:
            url: The URL of the image to extract metadata from.

        Returns:
            A Pandas DataFrame containing the following image metadata:
            * `source`: The source of the image.
            * `id`: The ID of the image.
            * `url`: The URL of the image.
            * `medium`: The medium of the image.
        """
        self.config = config
        self.database = database
        self.regex_for_image_links: str = regex_for_image_links
        self.medium = None

    @abstractmethod
    def _get_img_metadata(self, url: str) -> pd.DataFrame:
        """
        Receives a image URL and returns data frame with corresponding data.
        """
        pass

    def _get_links_img_url(self, url: str) -> List[str]:
        """
        Receives a search URL and returns all associated image URLs.

        Args:
            url: The search URL.

        Returns:
            A list of image URLs.
        """
        response = requests.get(url)
        link_elements = BeautifulSoup(response.text, "html.parser").findAll(
            "a", attrs={"href": re.compile(self.regex_for_image_links)}
        )
        links = [link_element["href"] for link_element in link_elements]
        return list(set(links))

    def save_pages_img_url_metadata(
        self, prefix_url_search: str, first_page: int, last_page: int
    ) -> None:
        """
        Scans a range of search URLs for image URLs, retrieves image metadata, and stores it in the database.

        Args:
            prefix_url_search: The base URL for searching images.
            first_page: The first page number to start scanning from.
            last_page: The last page number to scan up to.

        Returns:
            None
        """
        for medium in self.config["allowed_processes"]:
            if medium in prefix_url_search.upper():  # Search for Medium in link
                self.medium = medium
        for i in range(first_page, last_page + 1):
            url = prefix_url_search + str(i)
            if not self.database.check_log(DBAction.PAGE_PROCESS, url):
                logger.info("Processing page " + url)
                links = self._get_links_img_url(url)
                num_successes = 0
                num_errors = 0
                for link in links:
                    if not self.database.check_log(DBAction.IMAGE_PROCESS, link):
                        try:
                            self.database.save_data(
                                self._get_img_metadata(link), "images"
                            )
                            self.database.write_log(
                                self.__class__.__name__,
                                DBAction.IMAGE_PROCESS,
                                DBActionStatus.SUCCESS,
                                link,
                            )
                            logger.info(f"Added image metadata: {link}")
                            num_successes += 1
                        except Exception as e:
                            logger.error(
                                f"An exception of type {type(e).__name__} occurred: {str(e)} while getting image metadata {link}."
                            )
                            # Keep error info to try later
                            self.database.write_log(
                                self.__class__.__name__,
                                DBAction.IMAGE_PROCESS,
                                DBActionStatus.FAILURE,
                                link,
                            )
                            num_errors += 1
                    else:
                        logger.info(f"Image {link} already processed")
                logger.info(f"{str(num_successes)} entries added to DB")
                logger.info(
                    f"Failed to insert data for {str(num_errors)} images")
                self.database.write_log(
                    self.__class__.__name__,
                    DBAction.PAGE_PROCESS,
                    DBActionStatus.SUCCESS,
                    url,
                )
            else:
                logger.warning("Page " + url + " already processed")


class LibraryOfCongressCrawler(ImageMetadataCrawler):
    """An  class for crawling image metadata from the Library of Congress website.

    Attributes:
        config: The configuration for the image metadata crawler.
        database: The database to store the extracted image metadata in.
        regex_for_image_links: A regular expression to match image URLs.
        medium: The medium of the images to crawl.
    """

    def __init__(
        self,
        config: dict,
        database: Database,
        regex_for_image_links: str = "^https://www.loc.gov/pictures/item/",
    ) -> None:
        """Initializes the image metadata crawler.
        Args:
            config: The configuration data.
            database: The database to store the extracted image metadata in.
            regex_for_image_links: The regular expression used to identify image urls.
        """
        super().__init__(
            config=config,
            database=database,
            regex_for_image_links=regex_for_image_links,
        )

    def _get_img_metadata(self, url: str) -> pd.DataFrame:
        """Extracts image metadata from the given URL.

        Args:
            url: The URL of the image to extract metadata from.

        Returns:
            A Pandas DataFrame containing the following image metadata:
            * `source`: The source of the image.
            * `id`: The ID of the image.
            * `url`: The URL of the image.
            * `medium`: The medium of the image.
        """
        time.sleep(1)  # For avoiding rate limits
        response = requests.get(url)
        soup_mediums = BeautifulSoup(response.text, "html.parser").find_all(
            lambda tag: tag.name == "meta"
            and tag.has_attr("name")
            and tag["name"] in ["dc.format"]
        )
        medium = ",".join([tag["name"] for tag in soup_mediums])
        soup_for_links = BeautifulSoup(response.text, "html.parser").find_all(
            lambda tag: tag.name == "link"
            and tag.has_attr("type")
            and tag["type"] == "image/tif"
        )
        link = soup_for_links[0]["href"]
        # Get id from URL
        id_match = re.compile(r"/([0-9]+)").search(url)
        if id_match:
            id = id_match.group(1)
        else:
            logger.error("Could not find ID in URL {url}")
            raise ValueError
        df = pd.DataFrame(
            [
                {
                    "source": self.__class__.__name__,
                    "id": id,
                    "url": link,
                    "medium": medium,
                }
            ]
        )
        if self.medium:
            df[
                "medium"
            ] = (
                self.medium
            )  # We got the medium from the page link and this has priority
        return df


class GettyCrawler(ImageMetadataCrawler):
    def __init__(
        self,
        config: dict,
        database: Database,
        regex_for_image_links: str = r"^https://www\.getty\.edu/art/collection/objects/",
    ) -> None:
        """Initializes the image metadata crawler.
        Args:
            config: The configuration data.
            database: The database to store the extracted image metadata in.
            regex_for_image_links: The regular expression used to identify image urls.
        """
        super().__init__(
            config=config,
            database=database,
            regex_for_image_links=regex_for_image_links,
        )

        # example page URL - "https://www.getty.edu/art/collection/objects/161707/james-earle-mcclees-julian-vannerson-aaron-harlan-american-about-1859/").


class CornellCrawler(ImageMetadataCrawler):
    def __init__(
        self,
        config: dict,
        database: Database,
        regex_for_image_links: str = r"^https://www\.getty\.edu/art/collection/objects/",
    ) -> None:
        """Initializes the image metadata crawler.
        Args:
            config: The configuration data.
            database: The database to store the extracted image metadata in.
            regex_for_image_links: The regular expression used to identify image urls.
        """
        super().__init__(
            config=config,
            database=database,
            regex_for_image_links=regex_for_image_links,
        )

        # example page URL - "https://digital.library.cornell.edu/catalog/ss:544643").


class EastmanCrawler(ImageMetadataCrawler):
    def __init__(
        self,
        config: dict,
        database: Database,
        regex_for_image_links: str = r"^/objects/",
    ) -> None:
        """Initializes the image metadata crawler.
        Args:
            config: The configuration data.
            database: The database to store the extracted image metadata in.
            regex_for_image_links: The regular expression used to identify image urls.
        """
        super().__init__(
            config=config,
            database=database,
            regex_for_image_links=regex_for_image_links,
        )

        # example page URL - "view-source:https://collections.eastman.org/objects/194800/bt-babbitts-soap?ctx=924fc8d2-6506-4bad-aa82-41d905fdef2c&idx=56").
