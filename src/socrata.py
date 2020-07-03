from unidecode import unidecode as decode
from db import MariaDB_Connect
from datetime import datetime
from tqdm import tqdm

import sqlalchemy as db
import pandas as pd
import numpy as np
import requests
import json
import os

sess = requests.Session()
adapter = requests.adapters.HTTPAdapter(max_retries = 20)
sess.mount('http://', adapter)

class Socrata:
    def __init__(self, token, limit, db_user, db_password, db_host, db_database, start=0, json_path="data/JSON/"):
        self.token = token
        self.start = int(start)
        self.limit = int(limit)
        self.json_path = json_path
        self.user = db_user
        self.password = db_password
        self.host = db_host
        self.database = db_database
        self.metadata = []
        self.contador = 0

    def read_metadata(self):
        scroll_id = ""
        self.contador = 0
        index = 0
        while True:
            if index == 0:
                resp = sess.get("https://api.us.socrata.com/api/catalog/v1?domains=datos.gov.co&scroll_id={}&limit={}".format(scroll_id, self.limit))
                if resp.status_code == 200:
                    self.metadata = pd.DataFrame.from_dict(resp.json()["results"])
                    if not self.metadata.empty:
                        self.metadata = self.metadata.iloc[[item["type"] == "dataset" for item in self.metadata["resource"]]]
                        self.metadata["dataset_link"] = [item.split("www.datos.gov.co/d/")[-1] for item in self.metadata["permalink"]]
                        self.metadata["dataset_name"] = [dict(item)["name"] for item in self.metadata["resource"]]
                        category = []
                        for item in self.metadata["classification"]:
                            try:
                                cat = dict(item)["domain_category"]
                            except KeyError:
                                cat = None
                            category.append(cat)
                        self.metadata["category"] = category
                        scroll_id = self.metadata.iloc[-1, :][6]["id"]
                        self.contador += self.metadata.shape[0]
                        index += 1
                        print("Total Instances Fetched: {}".format(self.contador))
                    else:
                        break
                else:
                    break
            else:
                resp = sess.get("https://api.us.socrata.com/api/catalog/v1?domains=datos.gov.co&scroll_id={}&limit={}".format(scroll_id, self.limit))
                if resp.status_code == 200:
                    aux = pd.DataFrame(resp.json()["results"])
                    if not aux.empty:
                        aux = aux.iloc[[item["type"] == "dataset" for item in aux["resource"]]]
                        aux["dataset_link"] = [item.split("www.datos.gov.co/d/")[-1] for item in aux["permalink"]]
                        aux["dataset_name"] = [dict(item)["name"] for item in aux["resource"]]
                        category = []
                        for item in aux["classification"]:
                            try:
                                cat = dict(item)["domain_category"]
                            except KeyError:
                                cat = None
                            category.append(cat)
                        aux["category"] = category
                        scroll_id = aux.iloc[-1, :][6]["id"]
                        self.contador += aux.shape[0]
                        self.metadata = pd.concat([self.metadata, aux], axis=0)
                        index += 1
                        print("Total Instances Fetched: {}".format(self.contador))
                    else:
                        break
                else:
                    break
        print("Returning {} records".format(self.metadata.shape[0]))

    def download_dataset(self, item, updated=0, new=0, download=0):
        values = None
        complete_data = []
        if download == 1:
            data_final = None
            index = 0
            offset = 0
            records = sess.get("https://www.datos.gov.co/resource/{}.json?$select=count(*)".format(item["dataset_link"])).json()[0]
            keys = records.keys()
            records = int([records[key] for key in keys][0])
            iterations = np.ceil(records / self.limit)
            if iterations > 0:
                while index < iterations:
                    if index == 0:
                        url = "https://www.datos.gov.co/resource/{}.json?$$app_token={}&$limit={}&$offset={}".format(item["dataset_link"], self.token, self.limit, offset)
                        resp = sess.get(url)
                        if resp.status_code == 200:
                            data_final = pd.DataFrame(json.loads(resp.content, encoding="UTF-8"))
                            if not data_final.empty:
                                offset = (self.limit * index) + 1
                                index += 1
                            else:
                                index = iterations + 1
                        else:
                            print("Bad Request!")
                            index = iterations + 1
                    else:
                        url = "https://www.datos.gov.co/resource/{}.json?$$app_token={}&$limit={}&$offset={}".format(item["dataset_link"], self.token, self.limit, offset)
                        resp = sess.get(url)
                        if resp.status_code == 200:
                            aux = pd.DataFrame(json.loads(resp.content, encoding="UTF-8"))
                            if not aux.empty:
                                data_final = pd.concat([data_final, aux], axis=0, sort=True)
                                offset = (self.limit * index) + 1
                                index += 1
                            else:
                                index = iterations + 1
                        else:
                            print("Bad Request!")
                            index = iterations + 1

                complete_data.append({"metadata": item["metadata"],
                                    "resource": item["resource"],
                                    "dataset": item["dataset_name"],
                                    "data": data_final.to_dict()})

        values = {"id": item["resource"]["id"],
                "nombre": decode(item["resource"]["name"].replace(",", "")) if item["resource"]["name"] else "",
                "categoria": decode(item["category"]) if item["category"] else "",
                "entidad": decode(item["resource"]["attribution"].replace(",", "")) if item["resource"]["attribution"] else "",
                "descripcion": decode(item["resource"]["description"].replace(",", "")) if item["resource"]["description"] else "",
                "fecha_ejecucion": datetime.today().strftime("%Y-%m-%d"),
                "fecha_creacion": item["resource"]["createdAt"][0:10] if item["resource"]["createdAt"] else "",
                "fecha_actualizacion": item["resource"]["updatedAt"][0:10] if item["resource"]["updatedAt"] else "",
                "fecha_datos_actualizados": item["resource"]["data_updated_at"][0:10] if item["resource"]["data_updated_at"] else "",
                "fecha_metadata_actualizada": item["resource"]["metadata_updated_at"][0:10] if item["resource"]["metadata_updated_at"] else "",
                "actualizado": updated,
                "nuevo": new}
        return complete_data, values

    def update(self):
        datasets = ["4n4q-k399", "rpmr-utcd", "gnxj-bape", "aimg-uskh", "fzc7-w78v", "vfek-dafh"]
        data_map = {"4n4q-k399": "sanciones", 
            "rpmr-utcd": "integrado", 
            "gnxj-bape": "contratos" , 
            "aimg-uskh": "procesos", 
            "fzc7-w78v": "chip", 
            "vfek-dafh": "adquisiciones"}
        self.read_metadata()
        rows, _ = self.metadata.shape
        for i in tqdm(range(rows)):
            item = self.metadata.iloc[i, :]
            id_ = item["resource"]["id"]
            new_date = item["resource"]["data_updated_at"][0:10]
            db_connection = MariaDB_Connect(user=self.user,
                                        password=self.password,
                                        host=self.host,
                                        database=self.database)
            db_connection.connect_db()
            old_date = db_connection.search_by_id(id_)
            db_connection.close_db()
            download=0
            if old_date:
                if pd.to_datetime(old_date["updated_date"]) < pd.to_datetime(new_date):
                    if item["dataset_link"] in datasets:
                        if not os.path.exists("{}/{}".format(self.json_path, data_map[item["dataset_link"]])):
                            os.makedirs("{}/{}".format(self.json_path, data_map[item["dataset_link"]]), exist_ok=True)
                        download = 1
                    complete_data, values = self.download_dataset(item, updated=1, download=download)
                    db_connection = MariaDB_Connect(user=self.user,
                                        password=self.password,
                                        host=self.host,
                                        database=self.database)
                    db_connection.connect_db()
                    db_connection.update_dataset(values["id"], values["fecha_ejecucion"], values["fecha_actualizacion"], values["actualizado"], 0)
                    db_connection.close_db()
                    if download == 1:
                        self.save_to_disk(item, complete_data)
            else:
                if item["dataset_link"] in datasets:
                    if not os.path.exists("{}/{}".format(self.json_path, data_map[item["dataset_link"]])):
                        os.makedirs("{}/{}".format(self.json_path, data_map[dataset]), exist_ok=True)
                    download = 1
                complete_data, values = self.download_dataset(item, new=1, download=download)
                db_connection = MariaDB_Connect(user=self.user,
                                        password=self.password,
                                        host=self.host,
                                        database=self.database)
                db_connection.connect_db()
                db_connection.insert_dataset(values)
                db_connection.close_db()
                if download == 1:
                    self.save_to_disk(item, complete_data)

    def save_to_disk(self, item, complete_data):
        data_map = {"4n4q-k399": "sanciones", 
            "rpmr-utcd": "integrado", 
            "gnxj-bape": "contratos" , 
            "aimg-uskh": "procesos", 
            "fzc7-w78v": "chip", 
            "vfek-dafh": "adquisiciones"}
        with open("{}/{}/{}.json".format(self.json_path, data_map[item["resource"]["id"]], datetime.today().strftime("%Y-%m-%d")), "w", encoding="utf-8") as json_file:
                json_file.write(json.dumps(complete_data, indent=4, separators=(",", ":"), ensure_ascii=False))

    def save_to_db(self):
        data_map = {"4n4q-k399": "sanciones", 
            "rpmr-utcd": "integrado", 
            "gnxj-bape": "contratos" , 
            "aimg-uskh": "procesos", 
            "fzc7-w78v": "chip", 
            "vfek-dafh": "adquisiciones"}
        datasets = ["4n4q-k399", "rpmr-utcd", "gnxj-bape", "aimg-uskh", "fzc7-w78v", "vfek-dafh"]

        for dataset in datasets:
            db_connection = MariaDB_Connect(user=self.user,
                                            password=self.password,
                                            host=self.host,
                                            database=self.database)
            db_connection.connect_db()
            updated_date = db_connection.updated_date(dataset)
            filetoload = updated_date["fecha_actualizado"]
            db_connection.close_db()
            print("Loading {} file".format(data_map[dataset]))
            with open("{}/{}/{}.json".format(self.json_path, data_map[dataset], filetoload[0].strftime("%Y-%m-%d"))) as json_file:
                file_ = json.load(json_file)[0]["data"]
                file_ = pd.DataFrame(file_)
            names = [item.replace(" ", "_").replace("(", "_").replace(")", "_").lower() for item in file_.columns]
            file_.columns = names
            for col in names:
                file_[col] = [decode(row) if isinstance(row, str) else row for row in file_[col]]
            if data_map[dataset] == "contratos":
                del file_["urlproceso"]
            file_ = file_.where((pd.notnull(file_)), None)
            drop = "DROP TABLE IF EXISTS {};".format(data_map[dataset])
            sentence = "CREATE TABLE {} (id INTEGER AUTO_INCREMENT PRIMARY KEY, ".format(data_map[dataset])
            n = len(names)
            for i in range(len(names)):
                if i == n-1:
                    sentence += names[i] + " TEXT);"
                else:
                    sentence += names[i] + " TEXT, "
            db_connection = MariaDB_Connect(user=self.user,
                                        password=self.password,
                                        host=self.host,
                                        database=self.database)
            db_connection.connect_db()
            metadata = db.MetaData(bind=db_connection.connection)
            metadata.reflect()
            db_connection.connection.execute(drop)
            metadata.reflect()
            db_connection.connection.execute(sentence)
            metadata.reflect()
            query = db.insert(metadata.tables[data_map[dataset]])
            file_ = file_.to_dict("records")
            db_connection.connection.execute(query, file_)
            db_connection.close_db()

    def update_tables(self, src_path):
        db_connection = MariaDB_Connect(user=self.user,
                                            password=self.password,
                                            host=self.host,
                                            database=self.database)
        db_connection.connect_db()
        with open('{}/transformaciones.sql'.format(src_path), "r") as f:
            queries = f.read().split("\n")
        for query in queries:
            db_connection.connection.execute(query)
        db_connection.close_db()


class Socrata_Install(Socrata):
    def __init__(self, token, limit, db_user, db_password, db_host, db_database, start=0, to_cloud=1, json_path="data/JSON/"):
        super().__init__(token=token, 
                        limit=limit,  
                        start=start,
                        json_path=json_path, 
                        db_user=db_user, 
                        db_password=db_password, 
                        db_host=db_host, 
                        db_database=db_database)

    def download_data(self):
        db_connection = MariaDB_Connect(user=self.user,
                                        password=self.password,
                                        host=self.host,
                                        database=self.database)
        db_connection.connect_db()
        db_connection.init_db()
        db_connection.close_db()
        self.read_metadata()
        rows, _ = self.metadata.shape
        for i in tqdm(range(self.start, rows)):
            item = self.metadata.iloc[i, :]
            datasets = ["4n4q-k399", "rpmr-utcd", "gnxj-bape", "aimg-uskh", "fzc7-w78v", "vfek-dafh"]
            data_map = {"4n4q-k399": "sanciones", 
            "rpmr-utcd": "integrado", 
            "gnxj-bape": "contratos" , 
            "aimg-uskh": "procesos", 
            "fzc7-w78v": "chip", 
            "vfek-dafh": "adquisiciones"}
            download=0
            if item["dataset_link"] in datasets:
                if not os.path.exists("{}/{}".format(self.json_path, data_map[item["dataset_link"]])):
                    os.makedirs("{}/{}".format(self.json_path, data_map[item["dataset_link"]]), exist_ok=True)
                download = 1
            complete_data, values = self.download_dataset(item, download=download)
            if values:
                db_connection = MariaDB_Connect(user=self.user,
                                            password=self.password,
                                            host=self.host,
                                            database=self.database)
                db_connection.connect_db()
                if db_connection.search_by_id(values["id"]) is None:
                    db_connection.insert_dataset(values)
                db_connection.close_db()
                if download == 1:
                    self.save_to_disk(item, complete_data)
