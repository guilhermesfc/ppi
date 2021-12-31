import sqlalchemy
import pandas as pd
import datetime as dt

"""Class for interacting with DB"""


class DB:
    def __init__(self, db_name):
        self.engine = sqlalchemy.create_engine("sqlite:///" + db_name)

    def save_data(self, data, table, if_exists="append"):
        """Saves data into DB"""
        data.to_sql(table, con=self.engine, if_exists=if_exists)

    def write_log(self, source, action, status, url):
        self.save_data(
            pd.DataFrame(
                {
                    "source": source,
                    "action": [action],
                    "status": status,
                    "url": [url],
                    "date": [dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S")],
                }
            ),
            "log",
        )

    def check_log(self, action, url):
        """Checks wether entry exists in log"""
        try:
            query = (
                "select count(*) FROM log where url = '"
                + url.replace("'", "''")
                + "' and action = '"
                + action
                + "'"
            )
            return self.engine.execute(query).first()[0] > 0
        except:
            # Log table is not even created
            return False

    def next_image_download(self, medium=None):
        """Returns data for next image to download"""
        if medium:
            query = (
                "select img.source,img.id,img.url FROM images as img inner join mediums as me on img.id = me.id where img.url not in (select distinct url from log where action = 'download') and me.new_medium = '"
                + medium
                + "'"
            )
        else:
            query = "select source,id,url FROM images where url not in (select distinct url from log where action = 'download')"
        return self.engine.execute(query).fetchone()

    def get_medium(self, source, id):
        """Returns new medium for source/id"""
        query = (
            "select new_medium FROM mediums where source='"
            + source
            + "' and id='"
            + id
            + "'"
        )
        return self.engine.execute(query).fetchone()[0]

    def mediums_to_update(self):
        """Returns images to update medium"""
        return self.engine.execute("select * FROM images").fetchall()

    def get_all_mediums(self):
        """Returns list of source mediums"""
        query = "select distinct medium FROM images"
        return self.engine.execute(query).fetchall()

    def get_all_mediums_count(self):
        """Returns count of source mediums"""
        query = "select distinct medium, count(*) FROM images group by medium"
        return self.engine.execute(query).fetchall()
