import sqlalchemy as db
from sqlalchemy.pool import NullPool

class MariaDB_Connect:
    def __init__(self, user, password, host, database):
        self.user = user
        self.password = password
        self.host = host
        self.database = database
        self.engine = None
        self.connection = None
        self.metadata = None
        self.dataset = None

    def connect_db(self):
        SQLALCHEMY_DATABASE_URI = "mysql+pymysql://{}:{}@{}/{}".format(self.user, self.password, self.host, self.database)
        self.engine = db.create_engine(SQLALCHEMY_DATABASE_URI, poolclass=NullPool)
        self.connection = self.engine.connect()
        self.metadata = db.MetaData()
        self.dataset = db.Table("dataset",
                                self.metadata, 
                                db.Column("id", db.String(50), primary_key=True),
                                db.Column("nombre", db.Text),
                                db.Column("categoria", db.Text),
                                db.Column("entidad", db.Text),
                                db.Column("descripcion", db.Text),
                                db.Column("fecha_ejecucion", db.DateTime),
                                db.Column("fecha_creacion", db.DateTime),
                                db.Column("fecha_actualizacion", db.DateTime),
                                db.Column("fecha_datos_actualizados", db.DateTime),
                                db.Column("fecha_metadata_actualizada", db.DateTime),
                                db.Column("actualizado", db.String(1)),
                                db.Column("nuevo", db.String(1)))

    def init_db(self):
        self.metadata.create_all(self.engine)

    def insert_dataset(self, values):
        query = db.insert(self.dataset)
        self.connection.execute(query, values)

    def update_dataset(self, id_, executed_date, updated_date, updated, new):
        query = self.dataset.update().where(self.dataset.columns.id == id_).values({"fecha_ejecucion": executed_date, "fecha_actualizacion": updated_date, "actualizado": updated, "nuevo": new})
        self.connection.execute(query)
    
    def search_by_id(self, id_):
        query = db.select([self.dataset.columns.fecha_actualizacion]).where(self.dataset.columns.id == id_)
        results = self.connection.execute(query).fetchone()
        if results:
            return {"updated_date": results}
        else:
            return None

    def updated(self, id_):
        query = db.select([self.dataset.columns.actualizado]).where(self.dataset.columns.id == id_)
        results = self.connection.execute(query).fetchone()
        if results:
            return {"actualizado": results}
        else:
            return None

    def updated_date(self, id_):
        query = db.select([self.dataset.columns.fecha_ejecucion]).where(self.dataset.columns.id == id_)
        results = self.connection.execute(query).fetchone()
        if results:
            return {"fecha_actualizado": results}
        else:
            return None
    
    def close_db(self):
        self.connection.close()
        
