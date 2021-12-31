import yaml
import os
import re
import utils.database

"""Function for putting images into correct 'medium' folders"""


def move_images(balanced=True):

    with open("ppi/config.yaml", "r") as yamlfile:
        config = yaml.load(yamlfile, Loader=yaml.FullLoader)
    db = utils.database.DB(config["db_name"])
    images_per_med = {}  # Keep dictionary with # images per Medium folder
    base_path = config["dir"]["classify"]
    for folder in config["allowed_processes"]:
        if not os.path.exists(os.path.join(base_path, folder)):
            os.makedirs(
                os.path.join(base_path, folder)
            )  # Create target MEDIUM folders if non-existing
        images_per_med[folder] = len(os.listdir(os.path.join(base_path, folder)))
    images_in_med = {}  # Keep dictionary with files per medium
    files = os.listdir(config["dir"]["crop"])
    files = sorted(
        files, key=lambda x: os.stat(os.path.join(config["dir"]["crop"], x)).st_size
    )  # Sort files by size
    for file in files:
        source = re.compile(r"([^_]+)_").search(file).group(1)
        id = re.compile(r"_(.+)\.\w{3}").search(file).group(1)
        new_medium = db.get_medium(source, id)
        new_list = images_in_med.get(new_medium, [])
        new_list.append(file)
        images_in_med.update({new_medium: new_list})

        if balanced is False:
            for medium in images_per_med.keys():
                while len(images_in_med.get(medium, [])) > 0:
                    file = images_in_med[medium].pop()
                    os.rename(
                        os.path.join(config["dir"]["crop"], file),
                        os.path.join(config["dir"]["classify"], medium, file),
                    )  # Move file
                    images_per_med[medium] = images_per_med.get(medium, 0) + 1
        else:  # We want to create a balanced data set
            more_files = True
            while more_files:
                for min_medium in [
                    medium
                    for medium, b in zip(images_per_med.keys(), images_per_med.values())
                    if b == min(images_per_med.values())
                ]:
                    if len(images_in_med.get(min_medium, [])) > 0:
                        more_files = True
                        file = images_in_med[min_medium].pop()
                        os.rename(
                            os.path.join(config["dir"]["crop"], file),
                            os.path.join(config["dir"]["classify"], min_medium, file),
                        )  # Move file
                        images_per_med[min_medium] = (
                            images_per_med.get(min_medium, 0) + 1
                        )
    print("\n No more images. \n Current status:")
    print(images_per_med)
