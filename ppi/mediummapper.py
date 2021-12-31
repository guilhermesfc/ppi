import yaml
import re
import pandas as pd
import utils.database

"""Function and class for standardizing mediums (photographic processes) names"""


class MediumMapper:
    def __init__(self):
        # Read config
        with open("ppi/config.yaml", "r") as yamlfile:
            self.config = yaml.load(yamlfile, Loader=yaml.FullLoader)
        self.db = utils.database.DB(self.config["db_name"])
        self.proposal_mappings = self.get_proposal_mappings()
        self.show_stats()

    def propose_mapping(self, old_medium):
        """Defines rules for standardizing source mediums names"""
        curr_medium = re.sub(r"[^a-zA-Z\s]", " ", old_medium).upper().strip()
        curr_medium = re.sub(r"\s{2,}", " ", curr_medium)
        # RULES (ADJUST CODE ACCORDING TO YOUR CASE):
        # -------------------------------------------
        # REMOVE
        pattern = r"ALETHETYPE|ARTOTYPE|INKJET|CHRYSOTYPE|PANNOTYPE|CHROMOGENIC|OPALTYPE|LITHOGRAPH"
        if re.search(pattern, curr_medium):
            return "REMOVE"
        # ALBUMEN_PRINT
        if curr_medium in ["ALBUMEN PRINT", "ALBUMEN SILVER PRINT"] or re.search(
            r"ALBUMEN SILVER PRINT PRINTED", curr_medium
        ):
            return "ALBUMEN_PRINT"
        # AMBROTYPE
        elif curr_medium in ["AMBROTYPE", "TINTYPE"]:
            return "AMBROTYPE_TINTYPE_FERROTYPE"
        # CARBON_PRINT
        elif curr_medium in ["CARBON PRINT", "CARBON"]:
            return "CARBON_PRINT"
        # CYANOTYPE
        elif curr_medium in ["CYANOTYPE", "CYANOTYPES"]:
            return "CYANOTYPE"
        # DAGUERREOTYPE
        elif curr_medium == "DAGUERREOTYPE":
            return "DAGUERREOTYPE"
        # DOP
        elif curr_medium in [
            "BROMIDE PRINT",
            "SILVER BROMIDE PRINT",
            "GELATIN SILVER BROMIDE PRINTS",
            "GELATIN SILVER BROMIDE PRINT",
            "CHLOROBROMIDE PRINT",
            "GELATIN SILVER PRINT ON CHLORO BROMIDE PRINTING OUT PAPER",
        ]:
            return "DOP"
        elif curr_medium in ["GELATIN SILVER PRINT"]:
            return "DOP"
        # PLATINOTYPE_PALLADIOTYPE
        elif curr_medium in ["PLATINUM PRINT", "PLATINOTYPE", "PLATINUM"]:
            return "PLATINOTYPE_PALLADIOTYPE"
        # POP
        elif curr_medium in [
            "GELATINO CHLORIDE OR GELATIN CHLORIDE PRINTING OUT PRINT",
            "GELATIN SILVER CHLORIDE PRINT",
            "GELATIN SILVER CHLORIDE PRINTING OUT PAPER PRINT",
            "GELATIN SILVER PRINTING OUT PAPER PRINT",
            "COLLODION PRINT",
            "COLLODION SILVER PRINT",
            "COLLODION SILVER OR GELATIN SILVER PRINT",
            "COLLODION PRINTING-OUT PAPER PRINT",
            "POP",
        ]:
            return "POP"
        # SALTED_PAPER_PRINT
        elif curr_medium in ["SALTED PAPER PRINT", "SALT PRINT"]:
            return "SALTED_PAPER_PRINT"
        return "UNDEFINED"  # default case

    def get_proposal_mappings(self):
        """Creates mapping table"""
        old_medium = pd.DataFrame([item[0] for item in self.db.get_all_mediums()])
        new_medium = pd.DataFrame(
            [self.propose_mapping(item[0]) for item in self.db.get_all_mediums()]
        )
        result = pd.concat([old_medium, new_medium], axis=1)
        result.columns = ["old_medium", "new_medium"]
        return result

    def show_stats(self):
        db_counts = pd.DataFrame(
            self.db.get_all_mediums_count(), columns=["old_medium", "count"]
        )
        join = pd.merge(db_counts, self.proposal_mappings, on="old_medium", how="left")
        result = join.groupby(["new_medium"])["count"].sum().reset_index()
        print("Current stats:")
        print(result.sort_values(by=["count"]).to_string())

    def show_undefined(self):
        print(
            self.proposal_mappings[self.proposal_mappings["new_medium"] == "UNDEFINED"][
                "old_medium"
            ].to_string()
        )

    def map(self, old_medium):
        """Maps old medium to new medium"""
        try:
            res = self.proposal_mappings[
                self.proposal_mappings["old_medium"] == old_medium
            ]["new_medium"].item()
            return res
        except:
            raise TypeError("Could not find '" + old_medium + "' in mappings!")

    def update_mediums(self):
        """Updates mediums in DB"""
        result = self.db.mediums_to_update()
        data = pd.DataFrame.from_dict([{"source": "", "id": "", "new_medium": ""}])
        for image in result:
            new_medium = self.map(image["medium"])
            data = data.append(
                pd.DataFrame.from_dict(
                    [
                        {
                            "source": image["source"],
                            "id": image["id"],
                            "new_medium": new_medium,
                        }
                    ]
                )
            )
        self.db.save_data(data, "mediums", "replace")
