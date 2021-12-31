import urllib.request
import ssl
import os
import utils.database
import yaml
import shutil

"""Functions for downloading images into disk"""


def download_url(url, path):
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11",
        "Connection": "keep-alive",
    }
    request_ = urllib.request.Request(url, None, headers)
    context = ssl._create_unverified_context()
    response = urllib.request.urlopen(request_, context=context)
    # create a new file and write the image
    ext = url.split(".")[-1]
    if ext not in ("jpg", "jpeg", "tif"):
        try:
            ext = (
                response.info().get_filename().split(".")[-1]
            )  # we need to determine file extension
        except:
            ext = response.info()._headers[1][1].split("/")[-1]
    f = open(path + "." + ext, "wb")
    f.write(response.read())
    f.close()


def download_imgs(max=250, medium=None):
    """Goes through all images URLs in DB and downloads images into disk"""
    # Read config
    with open("ppi/config.yaml", "r") as yamlfile:
        config = yaml.load(yamlfile, Loader=yaml.FullLoader)
    db = utils.database.DB(config["db_name"])
    dir = config["dir"]["download"]
    if not os.path.exists(dir):
        os.makedirs(dir)
    result = db.next_image_download(medium)
    i = 0
    while result:
        if i <= max:
            path_file = os.path.join(dir, result["source"] + "_" + result["id"])
            print("Downloading:", result["url"])
            try:
                download_url(result["url"], path_file)
                db.write_log("", "download", "SUCCESS", result["url"])
                i += 1
            except:
                print("Failed to download \n ")
                db.write_log("", "download", "FAILURE", result["url"])
            # get next image to download
            result = db.next_image_download(medium)
        else:
            break
    print(
        "No more images to download"
        if i < max
        else "Maximum number of images downloaded"
    )
    print("Backing up")
    for file in os.listdir(config["dir"]["download"]):
        src_file_path = os.path.join(config["dir"]["download"], file)
        dst_file_path = os.path.join(config["dir"]["backup"], file)
        if not os.path.exists(dst_file_path):
            shutil.copy(src_file_path, dst_file_path)
    print("Back up done")
