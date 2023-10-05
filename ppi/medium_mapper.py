import re
import pandas as pd
from loguru import logger
from ppi.database import Database

"""Class for standardizing mediums (photographic processes) names"""


class MediumMapper:
    """A class for mapping old medium names to standardized medium names.

    Attributes:
        config: The configuration data.
        database: The database with the image mediums.
        proposal_mappings: A Pandas DataFrame containing the original medium mappings.
    """

    def __init__(self, config: dict, database: Database) -> None:
        """Initializes the medium mapper.

        Args:
            config: The configuration data.
            database: The database with the image mediums.
        """
        self.config = config
        self.database = database
        self.proposal_mappings = self._get_proposal_mappings()
        self.show_stats()

    def _propose_mapping(self, old_medium: str) -> str:
        """Defines rules for standardizing source mediums names.

        Args:
            old_medium: The old medium name.

        Returns:
            The standardized medium name.

        """
        medium = re.sub(r"[^a-zA-Z\s]", " ", old_medium).upper().strip()
        medium = re.sub(r"\s{2,}", " ", medium)
        # RULES (ADJUST CODE ACCORDING TO YOUR CASE):
        # -------------------------------------------
        # REMOVE
        pattern = r"ALETHETYPE|ARTOTYPE|INKJET|CHRYSOTYPE|PANNOTYPE|CHROMOGENIC|OPALTYPE|LITHOGRAPH"
        if re.search(pattern, medium):
            return "REMOVE"
        # ALBUMEN_PRINT
        if medium in ["ALBUMEN PRINT", "ALBUMEN SILVER PRINT"] or re.search(
            r"ALBUMEN SILVER PRINT PRINTED", medium
        ):
            return "ALBUMEN_PRINT"
        # AMBROTYPE
        elif medium in ["AMBROTYPE", "TINTYPE"]:
            return "AMBROTYPE_TINTYPE_FERROTYPE"
        # CARBON_PRINT
        elif medium in ["CARBON PRINT", "CARBON"]:
            return "CARBON_PRINT"
        # CYANOTYPE
        elif medium in ["CYANOTYPE", "CYANOTYPES"]:
            return "CYANOTYPE"
        # DAGUERREOTYPE
        elif medium == "DAGUERREOTYPE":
            return "DAGUERREOTYPE"
        # DOP
        elif medium in [
            "BROMIDE PRINT",
            "SILVER BROMIDE PRINT",
            "GELATIN SILVER BROMIDE PRINTS",
            "GELATIN SILVER BROMIDE PRINT",
            "CHLOROBROMIDE PRINT",
            "GELATIN SILVER PRINT ON CHLORO BROMIDE PRINTING OUT PAPER",
        ]:
            return "DOP"
        elif medium in ["GELATIN SILVER PRINT"]:
            return "DOP"
        # PLATINOTYPE_PALLADIOTYPE
        elif medium in ["PLATINUM PRINT", "PLATINOTYPE", "PLATINUM"]:
            return "PLATINOTYPE_PALLADIOTYPE"
        # POP
        elif medium in [
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
        elif medium in ["SALTED PAPER PRINT", "SALT PRINT"]:
            return "SALTED_PAPER_PRINT"
        return "UNDEFINED"  # default case

    def _get_proposal_mappings(self) -> pd.DataFrame:
        """Creates a Pandas DataFrame containing the proposed medium mappings.

        Returns:
            A Pandas DataFrame containing the proposed medium mappings.

        """
        all_mediums = self.database.get_all_mediums()
        if all_mediums:
            old_medium = pd.DataFrame(all_mediums)
            new_medium = pd.DataFrame(
                [self._propose_mapping(item) for item in all_mediums]
            )
            df = pd.concat([old_medium, new_medium], axis=1)
            df.columns = pd.Index(["old_medium", "new_medium"])
            return df
        else:
            return pd.DataFrame(columns=["old_medium", "new_medium"])

    def show_stats(self) -> None:
        """Prints statistics about the current medium mappings.

        Returns:
            None.
        """
        db_counts = pd.DataFrame(
            self.database.get_all_mediums_count(), columns=["old_medium", "count"]
        )
        join = pd.merge(db_counts, self.proposal_mappings, on="old_medium", how="left")
        result = join.groupby(["new_medium"])["count"].sum().reset_index()
        logger.info(f"Current stats: \n {result.sort_values(by=['count']).to_string()}")

    def show_undefined_mappings(self) -> None:
        """Prints a list of all the medium mappings that are undefined.

        Returns:
            None.
        """
        if (
            len(
                self.proposal_mappings[
                    self.proposal_mappings["new_medium"] == "UNDEFINED"
                ]["old_medium"]
            )
            > 0
        ):
            logger.info(
                self.proposal_mappings[
                    self.proposal_mappings["new_medium"] == "UNDEFINED"
                ]["old_medium"].to_string()
            )
        else:
            logger.info("No undefined medium descriptions.")

    def _map(self, old_medium) -> str:
        """Maps an old medium name to a standardized medium name.

        Args:
            old_medium: The old medium name.

        Returns:
            The standardized medium name.
        """
        try:
            res = self.proposal_mappings[
                self.proposal_mappings["old_medium"] == old_medium
            ]["new_medium"].item()
            return res
        except Exception as e:
            logger.error(
                f"An exception of type {type(e).__name__} occurred: {str(e)} while handling medium {old_medium}."
            )
            raise TypeError("Could not find '" + old_medium + "' in mappings")

    def update_mediums(self) -> None:
        """Updates the medium names in the database.

        Returns:
            None.
        """
        df = pd.DataFrame(columns=["source", "id", "new_medium"])
        images_to_update = self.database.get_images_to_update()
        if images_to_update:
            for image_metadata in images_to_update:
                source, id, medium = image_metadata
                new_medium = self._map(medium)
                new_row_df = pd.DataFrame.from_dict(
                    {
                        "source": [source],
                        "id": [id],
                        "new_medium": [new_medium],
                    }
                )
                df = pd.concat([df, new_row_df], ignore_index=True)
            self.database.save_data(data=df, table="mediums", if_exists="replace")
