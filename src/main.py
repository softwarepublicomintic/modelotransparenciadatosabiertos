from socrata import Socrata_Install

from time import time
import logging
import os

if __name__ == "__main__":
    token = os.environ["SOCRATA_TOKEN"]
    limit = os.environ["LIMIT"]
    start = os.environ["START"]
    json_path = os.environ["JSON_PATH"]
    log_dir = os.environ["LOG_PATH"]
    db_user = os.environ["MARIADB_USER"]
    db_password = os.environ["MARIADB_PASSWORD"]
    db_host = os.environ["MARIADB_HOST"]
    db_database = os.environ["MARIADB_DB"]
    install = int(os.environ["INSTALL"])
    src_path = os.environ["SRC_PATH"]

    logging.basicConfig(format="%(asctime)s - %(message)s",
                datefmt="%d-%b-%y %H:%M:%S",
                filename="{}/{}.log".format(log_dir, time()), 
                level=logging.DEBUG)

    logging.info("Starting downloading process using the following variables: ")
    logging.info("Token: %s", token)
    logging.info("Limit: %s", limit)
    logging.info("path: %s", json_path)
    logging.info("Install or Update: %s", install)
        
    if install == 1:
        print("Installing from Socrata")
        download_process = Socrata_Install(token=token, 
                                        limit=limit,
                                        db_user=db_user,
                                        db_password=db_password,
                                        db_host=db_host,
                                        db_database=db_database,
                                        start=start,
                                        json_path=json_path)
        download_process.download_data()
        download_process.save_to_db()
        download_process.update_tables(src_path)
    elif install == 2:
        print("Updating from Socrata")
        download_process = Socrata_Install(token=token, 
                                        limit=limit, 
                                        db_user=db_user,
                                        db_password=db_password,
                                        db_host=db_host,
                                        db_database=db_database,
                                        start=start, 
                                        json_path=json_path)
        download_process.update()
        download_process.save_to_db()
        download_process.update_tables(src_path)
    else:
        print("Installing and Updating from Socrata")
        download_process = Socrata_Install(token=token, 
                                        limit=limit, 
                                        db_user=db_user,
                                        db_password=db_password,
                                        db_host=db_host,
                                        db_database=db_database,
                                        start=start,
                                        json_path=json_path)
        download_process.download_data()
        download_process.update()
        download_process.save_to_db()
        download_process.update_tables(src_path)



