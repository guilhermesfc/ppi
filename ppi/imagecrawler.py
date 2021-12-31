import urllib.request
import ssl
import bs4
import re
import yaml
import pandas as pd
import utils.database

"""Classes for crawling the web for image data"""


class ImageCrawler:
    def __init__(self):
        # Read config
        import os

        print(os.getcwd())
        with open("ppi/config.yaml", "r") as yamlfile:
            self.config = yaml.load(yamlfile, Loader=yaml.FullLoader)
        self.db = utils.database.DB(self.config["db_name"])
        self.medium = None

    def get_img_data(self, url):
        """
        Receives image URL and returns data frame with corresponding data
        """
        # To implement in subclass
        pass

    def get_links_img_data(self, url):
        """
        Receives a search URL and returns all associated image URLs
        (e.g. URLs
         - "https://search.getty.edu/gateway/search?q=&cat=highlight&types=%22Photographs%22&highlights=%22Open%20Content%20Images%22&rows=10&srt=a&dir=s&dsp=0&img=1&pg=1"
         - "https://digital.library.cornell.edu/?f[type_tesim][]=cyanotypes&page=1"
         - "https://www.loc.gov/pictures/search/?va=exact&q=Cyanotypes.&fa=displayed%3Aanywhere&fi=format&sg=true&op=EQUAL&sp=1"
         - "https://collections.eastman.org/collections/20331/photography/objects/list?filter=date%3A1602%2C1990&page=1"
         )
        """
        context = ssl._create_unverified_context()
        html = urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}),
            context=context,
        ).read()
        objs = bs4.BeautifulSoup(html, "html.parser").findAll(
            "a", attrs={"href": re.compile(self.regex_links)}
        )
        links = list(set([self.prefix_url + obj["href"] for obj in objs]))
        return links

    def saves_pages_img_data(self, prefix_url_search, f_page, l_page):
        """
        Scans all search URLs between first page and last page given for image URLs.
        Saves image data into DB
        """
        for medium in self.config["allowed_processes"]:
            if medium in prefix_url_search.upper():  # Search for medium in link
                self.medium = medium
        for i in range(f_page, l_page + 1):
            url = prefix_url_search + str(i)
            # Confirm we have not processed page before
            if not self.db.check_log("page process", url):
                print("Processing page " + url)
                curr_links = self.get_links_img_data(url)
                success = error = 0
                for link in curr_links:
                    # Confirm we have not retrieved image info before
                    if not self.db.check_log("image process", link):
                        try:
                            self.db.save_data(self.get_img_data(link), "images")
                            # Add image to log
                            self.db.write_log(
                                self.__class__.__name__,
                                "image process",
                                "SUCCESS",
                                link,
                            )
                            success += 1
                        except:
                            # Keep error info to try later
                            self.db.write_log(
                                self.__class__.__name__,
                                "image process",
                                "FAILURE",
                                link,
                            )
                            error += 1
                    else:
                        print("Image " + link + " already processed")
                print(str(success) + " entries added to DB")
                print("Failed to insert data for " + str(error) + " images")
                # Add page to log
                self.db.write_log(
                    self.__class__.__name__, "page process", "SUCCESS", url
                )
            else:
                print("Page " + url + " already processed")
        self.medium = None


class GettyCrawler(ImageCrawler):
    def __init__(self):
        super().__init__()
        self.prefix_url = ""
        self.regex_links = r"^https://www\.getty\.edu/art/collection/objects/"

    def get_img_data(self, url):
        """
        Receives image URL and returns data frame with corresponding data
        (e.g. URL - "https://www.getty.edu/art/collection/objects/161707/james-earle-mcclees-julian-vannerson-aaron-harlan-american-about-1859/")
        """

        def tag_metadata(tag):  # Identifies tags with metadata to extract
            return (
                tag.name == "meta"
                and tag.has_attr("name")
                and tag.has_attr("content")
                and tag["name"] in ["image", "medium", "thumbimage"]
            )

        def get_ref(url):  # Aux function
            pattern = r"([0123456789]+[A-Z0-9]*)"
            header = re.search(pattern, url)
            return header.group()

        html = urllib.request.urlopen(url).read()
        data_df = pd.DataFrame()
        for data in bs4.BeautifulSoup(html, "html.parser").find_all(tag_metadata):
            curr_Series = pd.Series([data["name"], data["content"]])
            data_df = data_df.append(curr_Series, ignore_index=True)
        data_fr = data_df.transpose()
        data_fr.columns = data_fr.iloc[0, :]
        data_fr = data_fr.drop([0])
        # Keep image URL
        if "image" in data_fr.columns:
            data_fr.insert(
                0,
                "url",
                data_fr["image"].apply(
                    lambda x: "https://media.getty.edu/museum/images/web/download/"
                    + get_ref(x)
                    + ".jpg"
                ),
            )
            data_fr = data_fr.drop(columns=["image"])
            if "thumbimage" in data_fr.columns:
                data_fr = data_fr.drop(columns=["thumbimage"])
        elif "thumbimage" in data_fr.columns:
            data_fr.insert(0, "url", data_fr["thumbimage"])
            data_fr = data_fr.drop(columns=["thumbimage"])
        else:
            raise Exception("No image available for download")
        data_fr.insert(
            0, "id", re.search(r"([0123456789]+[A-Z0-9]*)", url).group()
        )  # Add ID
        data_fr.insert(0, "source", self.__class__.__name__)
        return data_fr


class CornellCrawler(ImageCrawler):
    def __init__(self):
        super().__init__()
        self.prefix_url = "https://digital.library.cornell.edu"
        self.regex_links = "^/catalog/ss:"

    def get_img_data(self, url):
        """
        Receives image URL and returns data frame with corresponding data
        (e.g. URL - "https://digital.library.cornell.edu/catalog/ss:544643")
        """

        def tag_metadata(tag):  # Identifies tags with metadata to extract
            return tag.name == "dd" and tag["class"] in [
                ["blacklight-title_tesim"],
                ["blacklight-type_tesim"],
                ["blacklight-date_tesim"],
                ["blacklight-creator_tesim"],
                ["blacklight-id_number_tesim"],
            ]

        html = urllib.request.urlopen(url).read()
        data_df = pd.DataFrame()
        for data in bs4.BeautifulSoup(html, "html.parser").find_all(tag_metadata):
            curr_Series = pd.Series([data["class"][0], data.get_text()])
            data_df = data_df.append(curr_Series, ignore_index=True)
        # get link
        link_data = bs4.BeautifulSoup(html, "html.parser").find_all(
            lambda tag: tag.name == "a"
            and tag.has_attr("title")
            and tag["title"] == "Download this image"
        )
        curr_Series = pd.Series(["link", link_data[0]["href"]])
        data_fr = data_df.append(curr_Series, ignore_index=True).transpose().drop([0])
        data_fr.insert(0, "source", self.__class__.__name__)
        data_fr.columns = ["source", "id", "medium", "url"]
        data_fr = data_fr[["source", "id", "url", "medium"]]
        if self.medium:
            data_fr[
                "medium"
            ] = self.medium  # We got the medium from the page link -> this has priority
        return data_fr


class CongressCrawler(ImageCrawler):
    def __init__(self):
        super().__init__()
        self.prefix_url = ""
        self.regex_links = "^https://www.loc.gov/pictures/item/"

    def get_img_data(self, url):
        """
        Receives image URL and returns data frame with corresponding data
        (e.g. URL - "https://www.loc.gov/pictures/item/2007662272/")
        """

        def tag_metadata(tag):  # Identifies tags with metadata to extract
            return (
                tag.name == "meta"
                and tag.has_attr("name")
                and tag["name"] in ["dc.format"]
            )

        html = urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        ).read()
        data_df = pd.DataFrame()
        for data in bs4.BeautifulSoup(html, "html.parser").find_all(tag_metadata):
            curr_Series = pd.Series([data["name"], data["content"]])
            data_df = data_df.append(curr_Series, ignore_index=True)
        # get link
        if not curr_Series:
            raise Exception("Medium not found")
        data_df = data_df.groupby([0])[1].apply(",".join).reset_index()
        link_data = bs4.BeautifulSoup(html, "html.parser").find_all(
            lambda tag: tag.name == "link"
            and tag.has_attr("type")
            and tag["type"] == "image/tif"
        )
        curr_Series = pd.Series(["link", "https:" + link_data[0]["href"]])
        data_df = data_df.append(curr_Series, ignore_index=True)
        # get id from URL
        curr_Series = pd.Series(["id", re.compile(r"/([0-9]+)").search(url).group(1)])
        data_fr = data_df.append(curr_Series, ignore_index=True).transpose().drop([0])
        data_fr.insert(0, "source", self.__class__.__name__)
        data_fr.columns = ["source", "medium", "url", "id"]
        data_fr = data_fr[["source", "id", "url", "medium"]]
        if self.medium:
            data_fr[
                "medium"
            ] = self.medium  # We got the medium from the page link -> this has priority
        return data_fr


class EastmanCrawler(ImageCrawler):
    def __init__(self):
        super().__init__()
        self.prefix_url = "https://collections.eastman.org"
        self.regex_links = "^/objects/"

    def get_img_data(self, url):
        """
        Receives image URL and returns data frame with corresponding data
        (e.g. URL - "view-source:https://collections.eastman.org/objects/194800/bt-babbitts-soap?ctx=924fc8d2-6506-4bad-aa82-41d905fdef2c&idx=56")
        """

        def tag_metadata(tag):  # Identifies tags with metadata to extract
            return (
                tag.name == "div"
                and tag.has_attr("class")
                and tag["class"] in [["detailField", "mediumField"]]
            )

        context = ssl._create_unverified_context()
        html = urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}),
            context=context,
        ).read()
        data_df = pd.DataFrame()
        for data in bs4.BeautifulSoup(html, "html.parser").find_all(tag_metadata):
            curr_Series = pd.Series(["", data.string])
            data_df = data_df.append(curr_Series, ignore_index=True)
        # get link
        link_data = re.compile(
            r"https://collections.eastman.org/internal/media/dispatcher/[0-9]+/.*full"
        ).search(html.decode())[0]
        curr_Series = pd.Series(["link", link_data])
        data_df = data_df.append(curr_Series, ignore_index=True)
        # get id from URL
        curr_Series = pd.Series(
            ["id", re.compile(r"objects/([0-9]+)").search(url).group(1)]
        )
        data_fr = data_df.append(curr_Series, ignore_index=True).transpose().drop([0])
        data_fr.insert(0, "source", self.__class__.__name__)
        data_fr.columns = ["source", "medium", "url", "id"]
        data_fr = data_fr[["source", "id", "url", "medium"]]
        if self.medium:
            data_fr[
                "medium"
            ] = self.medium  # We got the medium from the page link -> this has priority
        return data_fr
