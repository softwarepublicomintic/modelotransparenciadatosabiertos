#!/usr/bin/bash

## CONFIGURACIÓN DE INSTALACIÓN

source parameters.config

if [ $? == 1 ]
then
    echo "Carga incorrecta del archivo de configuración"
else
    if [ $FRESH_INSTALL == 1 ]
    then
        cd $PROJECT_PATH
        mkdir $DATA_PATH $LOG_PATH $JSON_PATH $MARIADB_PATH
        python3 $SRC_PATH/main.py
        sudo systemctl restart httpd
    else
        cd $PROJECT_PATH
        python3 $SRC_PATH/main.py
        sudo systemctl restart httpd
    fi
fi
