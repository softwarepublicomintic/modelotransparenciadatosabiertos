import os
import requests
import base64
import math
import json
import pandas as pd
import numpy as np
from flask import Flask
import plotly.graph_objs as go
from datetime import datetime as dt
from unidecode import unidecode as decode

import dash
import dash_table
import dash_core_components as dcc
import dash_html_components as html
import dash_table.FormatTemplate as FormatTemplate

from db import MariaDB_Connect
from sqlalchemy.sql import text

from app import app

exec(open("/var/www/modelodatosabiertos/db_credentials.sh").read())
# exec(open("db_credentials.sh").read())

db_user = MARIADB_USER
db_password = MARIADB_PASSWORD
db_host = MARIADB_HOST
db_database = MARIADB_DB

colores = ["#F42F63", "#FFAB00", "#008E65", "#3366CC"]

fips_sanciones = pd.read_csv("/var/www/modelodatosabiertos/src/data/fips_sanciones.csv", sep=",", encoding="UTF-8")
# fips_sanciones = pd.read_csv("src/data/fips_sanciones.csv", sep=",", encoding="UTF-8")
fips_sanciones.departamento = [item.upper() for item in fips_sanciones.departamento]
fips_contratos = pd.read_csv("/var/www/modelodatosabiertos/src/data/fips_contratos.csv", sep=",", encoding="UTF-8")
# fips_contratos = pd.read_csv("src/data/fips_contratos.csv", sep=",", encoding="UTF-8")
fips_contratos.departamento = [item.upper() for item in fips_contratos.departamento]
with open("/var/www/modelodatosabiertos/src/data/mapa_geojson.json") as json_file:
# with open("src/data/mapa_geojson.json") as json_file:
    geoJSON = json.load(json_file)

for i in range(fips_contratos.shape[0]):
    for j in range(33):
        if geoJSON["features"][j]["properties"]["NOMBRE_DPT"] == fips_contratos.loc[i, "departamento"]:
            geoJSON["features"][j]["id"] = fips_contratos.loc[i, "fips"]

#################################################

# Contratos
contratos_departamento = """
    SELECT * FROM ciudad_valor_promedio;
"""

contratos_objeto = """
    SELECT * FROM objeto_conteo;
"""

contratos_modalidad = """
    SELECT * FROM modalidad_conteo;
"""

contratos_entidad = """
    SELECT * FROM entidad_contratista_conteo;
"""

# Sanciones
sanciones_orden = """
    SELECT orden,
        COUNT(*) AS conteo,
        ROUND(AVG(valor_sancion)) AS promedio_sancion
FROM sanciones
GROUP BY 1
ORDER BY 2 DESC;
"""

sanciones_contratista = """
    SELECT ciudad,
        nombre_entidad,
        nombre_contratista,
        documento_contratista,
        COUNT(*) AS conteo,
        ROUND(AVG(valor_sancion)) AS promedio_sancion
FROM sanciones
WHERE ciudad <> ''
GROUP BY 1, 2, 3, 4
ORDER BY 6 DESC;
"""

sanciones_contratante = """
    SELECT ciudad,
        entidad,
        nit_entidad,
        COUNT(*) AS conteo,
        ROUND(AVG(valor_sancion)) AS promedio_sancion
FROM sanciones
WHERE ciudad <> ''
GROUP BY 1, 2
ORDER BY 4 DESC;
"""

sanciones_ciudad = """
    SELECT ciudad,
        COUNT(*) AS conteo,
        ROUND(AVG(valor_sancion)) AS promedio_sancion
FROM sanciones
WHERE ciudad <> ''
GROUP BY 1
ORDER BY 2 DESC;
"""

sanciones_entidad_contratista_bogota = """
    SELECT A.entidad,
        B.nombre_contratista,
        B.conteo,
        A.conteo_entidad,
        B.promedio_sancion
    FROM
    (
        SELECT ciudad,
            entidad,
            COUNT(*) as conteo_entidad
        FROM sanciones
        WHERE ciudad <> ''
        AND ciudad = 'BOGOTÁ D.C.'
        GROUP BY 1, 2
    ) A
    INNER JOIN
    (
        SELECT ciudad,
            entidad,
            nombre_contratista AS nombre_contratista,
            COUNT(*) AS conteo,
            ROUND(AVG(valor_sancion)) AS promedio_sancion
        FROM sanciones
        WHERE ciudad <> ''
        AND ciudad = 'BOGOTÁ D.C.'
        GROUP BY 1, 2, 3
    ) B
    ON A.entidad = B.entidad;
"""

# Alertas
pregunta2 = """
SELECT * FROM pregunta2;
"""

pregunta3 = """
SELECT nombre_de_la_entidad, Gini FROM gini;
"""

pregunta4 = """
SELECT * FROM plurales;
"""

pregunta5 = """
SELECT * FROM no_competitivos;
"""

pregunta6 = """
SELECT * FROM chip_no_secop;
"""

pregunta7 = """
SELECT * FROM chip_no_adquisiciones;
"""

db_connection = MariaDB_Connect(user=db_user,
                                password=db_password,
                                host=db_host,
                                database=db_database)
db_connection.connect_db()
datos_contratos_departamento = db_connection.connection.execute(contratos_departamento).fetchall()
datos_contratos_departamento = pd.DataFrame(datos_contratos_departamento, columns=["departamento", "conteo", "promedio_contratos"])
datos_contrato_objeto = db_connection.connection.execute(contratos_objeto).fetchall()
datos_contrato_objeto = pd.DataFrame(datos_contrato_objeto, columns=["objeto_contratar", "conteo"])
datos_contrato_modalidad = db_connection.connection.execute(contratos_modalidad).fetchall()
datos_contrato_modalidad = pd.DataFrame(datos_contrato_modalidad, columns=["modalidad", "conteo"])
datos_contratos_entidad = db_connection.connection.execute(contratos_entidad).fetchall()
datos_contratos_entidad = pd.DataFrame(datos_contratos_entidad, columns=["ciudad", "nombre_entidad", "nombre_contratista", "conteo", "promedio_contrato"])
db_connection.close_db()

datos_contratos_departamento = pd.merge(fips_contratos, datos_contratos_departamento, on="departamento")
datos_contratos_departamento["departamento"] = [row["departamento"].title() if row["departamento"] is not None else "" for index, row in datos_contratos_departamento.iterrows()]
datos_contratos_entidad = pd.merge(fips_contratos, datos_contratos_entidad, left_on="departamento", right_on="ciudad")
datos_contratos_entidad["departamento"] = [row["departamento"].title() if row["departamento"] is not None else "" for index, row in datos_contratos_entidad.iterrows()]
datos_contratos_entidad["nombre_entidad"] = [row["nombre_entidad"].title() if row["nombre_entidad"] is not None else "" for index, row in datos_contratos_entidad.iterrows()]
datos_contratos_entidad["nombre_contratista"] = [row["nombre_contratista"].title() if row["nombre_contratista"] is not None else "" for index, row in datos_contratos_entidad.iterrows()]

mapa_contratos = go.Figure(
    go.Choroplethmapbox(geojson=geoJSON,
                        locations=datos_contratos_departamento.fips,
                        z=datos_contratos_departamento.conteo,
                        text=datos_contratos_departamento.departamento,
                        colorscale=colores,
                        zmin=min(datos_contratos_departamento.conteo),
                        zmax=max(datos_contratos_departamento.conteo),
                        marker_opacity=0.7,
                        marker_line_width=2))

mapa_contratos.update_layout(mapbox_style="carto-positron",
                            mapbox_zoom=4.1,
                            mapbox_center={"lat": 6.25184, "lon": -75.56359},
                            autosize=True,
                            height=400)

mapa_contratos.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})

contratos_objeto = go.Scatter(x=datos_contrato_objeto.conteo,
                        y=datos_contrato_objeto.objeto_contratar,
                        mode='markers',
                        marker=dict(color="#069169", size=20))

contratos_modalidad = go.Pie(values=datos_contrato_modalidad.conteo,
                            labels=datos_contrato_modalidad.modalidad,
                            textposition="inside",
                            marker_colors=["#3366CC", "#FFAB00", "#F42E62", "#069169", "#F3561F", "#FFF2FA", "#A80512", "#2BFCA7", "#2DF4F9", "#3772FF"])
########################################

db_connection = MariaDB_Connect(user=db_user,
                                password=db_password,
                                host=db_host,
                                database=db_database)
db_connection.connect_db()
data_sancion_orden = db_connection.connection.execute(sanciones_orden).fetchall()
data_sancion_orden = pd.DataFrame(data_sancion_orden, columns=["orden", "conteo", "promedio_sancion"])
datos_sancion_contratista = db_connection.connection.execute(sanciones_contratista).fetchall()
datos_sancion_contratista = pd.DataFrame(datos_sancion_contratista, columns=["ciudad", "entidad", "nombre_contratista", "documento_contratista", "conteo", "promedio_sancion"])
datos_sancion_contratista.ciudad = [decode(item).upper() for item in datos_sancion_contratista.ciudad]
datos_sancion_contratante = db_connection.connection.execute(sanciones_contratante).fetchall()
datos_sancion_contratante = pd.DataFrame(datos_sancion_contratante, columns=["ciudad", "nombre_entidad", "nit_entidad", "conteo", "promedio_sancion"])
datos_sancion_contratante.ciudad = [decode(item).upper() for item in datos_sancion_contratante.ciudad]
datos_sanciones_ciudad = db_connection.connection.execute(sanciones_ciudad).fetchall()
datos_sanciones_ciudad = pd.DataFrame(datos_sanciones_ciudad, columns=["ciudad", "conteo", "promedio_sancion"])
datos_sanciones_ciudad.ciudad = [decode(item).upper() for item in datos_sanciones_ciudad.ciudad]
datos_bogota = db_connection.connection.execute(sanciones_entidad_contratista_bogota).fetchall()
datos_bogota = pd.DataFrame(datos_bogota, columns=["entidad", "nombre_contratista", "conteo", "conteo_entidad", "promedio_sancion"])
db_connection.close_db()

datos_sanciones_ciudad = pd.merge(fips_sanciones, datos_sanciones_ciudad, left_on="departamento", right_on="ciudad")
datos_sanciones_ciudad["ciudad"] = [row["ciudad"].title() if row["ciudad"] is not None else "" for index, row in datos_sanciones_ciudad.iterrows()]
data_sancion_orden["orden"] = [row["orden"].title() if row["orden"] is not None else "" for index, row in data_sancion_orden.iterrows()]
datos_sancion_contratante = pd.merge(fips_sanciones, datos_sancion_contratante, left_on="departamento", right_on="ciudad")
datos_sancion_contratante["departamento"] = [row["departamento"].title() if row["departamento"] is not None else "" for index, row in datos_sancion_contratante.iterrows()]
datos_sancion_contratante["nombre_entidad"] = [row["nombre_entidad"].title() if row["nombre_entidad"] is not None else "" for index, row in datos_sancion_contratante.iterrows()]
datos_sancion_contratista = pd.merge(fips_sanciones, datos_sancion_contratista, left_on="departamento", right_on="ciudad")
datos_sancion_contratista["departamento"] = [row["departamento"].title() if row["departamento"] is not None else "" for index, row in datos_sancion_contratista.iterrows()]
datos_sancion_contratista["entidad"] = [row["entidad"].title() if row["entidad"] is not None else "" for index, row in datos_sancion_contratista.iterrows()]
datos_sancion_contratista["nombre_contratista"] = [row["nombre_contratista"].title() if row["nombre_contratista"] is not None else "" for index, row in datos_sancion_contratista.iterrows()]
datos_mapa = datos_sancion_contratante.groupby(["departamento", "fips"], as_index=False).conteo.sum()

mapa_sanciones = go.Figure(
    go.Choroplethmapbox(geojson=geoJSON,
                        locations=datos_mapa.fips,
                        z=datos_mapa.conteo,
                        text=datos_mapa.departamento,
                        colorscale=colores,
                        zmin=min(datos_mapa.conteo),
                        zmax=max(datos_mapa.conteo),
                        marker_opacity=0.7,
                        marker_line_width=2))

mapa_sanciones.update_layout(mapbox_style="carto-positron",
                            mapbox_zoom=4.1,
                            mapbox_center={"lat": 6.25184, "lon": -75.56359},
                            autosize=True,
                            height=400)

mapa_sanciones.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})

mapa_sanciones_monto = go.Figure(
    go.Choroplethmapbox(geojson=geoJSON,
                        locations=datos_mapa.fips,
                        z=datos_sanciones_ciudad.promedio_sancion,
                        text=datos_sanciones_ciudad.ciudad,
                        colorscale=colores,
                        zmin=min(datos_sanciones_ciudad.promedio_sancion),
                        zmax=max(datos_sanciones_ciudad.promedio_sancion),
                        marker_opacity=0.7,
                        marker_line_width=2))

mapa_sanciones_monto.update_layout(mapbox_style="carto-positron",
                            mapbox_zoom=4.1,
                            mapbox_center={"lat": 6.25184, "lon": -75.56359},
                            autosize=True,
                            height=400)

mapa_sanciones_monto.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})

sancion_orden = go.Pie(values=data_sancion_orden.conteo,
                    labels=data_sancion_orden.orden,
                    textposition="inside")

sanciones_bogota = go.Scatter(x=datos_bogota.conteo_entidad,
                            y=datos_bogota.promedio_sancion,
                            mode="markers",
                            marker=dict(
                                color=datos_bogota.conteo*10,
                                opacity=0.7,
                                showscale=True,
                                size=datos_bogota.conteo*5),
                            text=[("Entidad: {entidad}" +
                                    "<br>Contratista: {contratista}" +
                                    "<br>Contratos Sancionados Contratista: {sancionados_contratista}" +
                                    "<br>Contratos Sancionados Entidad: {sancionados_entidad}" +
                                    "<br>Promedio Sanción: {promedio_sancion}").format(entidad=row["entidad"],
                                                                                        contratista=row["nombre_contratista"],
                                                                                        sancionados_contratista=row["conteo"],
                                                                                        sancionados_entidad=row["conteo_entidad"],
                                                                                        promedio_sancion=row["promedio_sancion"]) for index, row in datos_bogota.iterrows()])

db_connection = MariaDB_Connect(user=db_user,
                                password=db_password,
                                host=db_host,
                                database=db_database)
db_connection.connect_db()
datos_p2 = db_connection.connection.execute(pregunta2).fetchall()
datos_p2 = pd.DataFrame(datos_p2, columns=["entidad", "activos", "nuevos", "proporcion"])
datos_p2["entidad"] = [row["entidad"].title() if row["entidad"] is not None else "" for index, row in datos_p2.iterrows()]
datos_p3 = db_connection.connection.execute(pregunta3).fetchall()
datos_p3 = pd.DataFrame(datos_p3, columns=["entidad", "gini"])
datos_p3["entidad"] = [row["entidad"].title() if row["entidad"] is not None else "" for index, row in datos_p3.iterrows()]
datos_p4 = db_connection.connection.execute(pregunta4).fetchall()
datos_p4 = pd.DataFrame(datos_p4, columns=["entidad", "ano", "adjudicados", "valor_adjudicado", "plurales", "prop_plurales", "prop_valor_plurales"])
datos_p4["entidad"] = [row["entidad"].title() if row["entidad"] is not None else "" for index, row in datos_p4.iterrows()]
datos_p5 = db_connection.connection.execute(pregunta5).fetchall()
datos_p5 = pd.DataFrame(datos_p5, columns=["entidad", "ejecutados", "especificos", "adjudicados_no_competitivos"])
datos_p5["entidad"] = [row["entidad"].title() if row["entidad"] is not None else "" for index, row in datos_p5.iterrows()]
datos_p6 = db_connection.connection.execute(pregunta6).fetchall()
datos_p6 = pd.DataFrame(datos_p6, columns=["entidad","departamento"])
datos_p6["entidad"] = [row["entidad"].title() if row["entidad"] is not None else "" for index, row in datos_p6.iterrows()]
datos_p6["departamento"] = [row["departamento"].title() if row["departamento"] is not None else "" for index, row in datos_p6.iterrows()]
datos_p7 = db_connection.connection.execute(pregunta7).fetchall()
datos_p7 = pd.DataFrame(datos_p7, columns=["entidad", "departamento"])
datos_p7["entidad"] = [row["entidad"].title() if row["entidad"] is not None else "" for index, row in datos_p7.iterrows()]
datos_p7["departamento"] = [row["departamento"].title() if row["departamento"] is not None else "" for index, row in datos_p7.iterrows()]
db_connection.close_db()

opts = datos_p7.groupby("departamento").count().index.tolist()
opts = [{"label": i, "value": i} for i in opts]

##############################################

layout = html.Div(
        children=[
            dcc.Tabs(
                id="tab-territorio", 
                value="alertas",
                className="contenedor_pestanas",
                    children=[
                        dcc.Tab(
                            label="Datos en Territorio",
                            className="pestanas",
                            children=[
                                dcc.Tabs(
                                    id="subtab-territorio",
                                    value="contratos",
                                    className="contenedor_subpestanas",
                                    children=[
                                        dcc.Tab(
                                            label="Contratos ", 
                                            value="contratos",
                                            className="subpestanas"
                                        ),
                                        dcc.Tab(
                                            label="Sanciones ", 
                                            value="sanciones",
                                            className="subpestanas"
                                        )
                                    ]
                                ),
                                html.Div(id='contenido-subtab-territorio')
                            ]
                        ),
                        dcc.Tab(
                            label="Identifique alertas", 
                            value="alertas",
                            className="pestanas"
                        )
                    ]
            ),
            html.Div(id='contenido-territorio'),
        ],
        className="body"
    )

image_filename = "/var/www/modelodatosabiertos/src/img/contratos.png"
# image_filename = "src/img/contratos.png"
encoded_image = base64.b64encode(open(image_filename, 'rb').read())

image_filename = "/var/www/modelodatosabiertos/src/img/sanciones.png"
# image_filename = "src/img/sanciones.png"
encoded_sanciones_image = base64.b64encode(open(image_filename, 'rb').read())

image_filename = "/var/www/modelodatosabiertos/src/img/alertas.jpg"
# image_filename = "src/img/alertas.jpg"
encoded_alerts_image = base64.b64encode(open(image_filename, 'rb').read())

def contratos():
    return html.Div(
            className="body",
            children=[
                html.Div(
                    className="contenedor_externo_exp",
                    children=[
                        html.Div(
                            className="contenedor_graficas_derecha_exp",
                            children=[
                                html.Div(
                                    className="contenedor_textos_externos",
                                    children=[
                                        dcc.Markdown(
                                            className="textos_aclaratorios_exp",
                                            children="""En los siguientes gráficas podrá encontrar información asociada a los procesos de Contratación Pública, mostrando de una manera sencilla, información de interés para todos los ciudadanos. En esta sección podrá encontrar información asociada al valor de contratos por departamento, tipos de contratos otorgados y el tipo de contratación. Las visualizaciones hechas en esta página son realizadas a partir del conjunto de datos abiertos del SECOP Integrado, que contienen toda la información de los procesos de compra pública que han finalizado con un contrato."""
                                        )
                                    ]
                                )
                            ]
                        ),
                        html.Div(
                            className="contenedor_graficas_izquierda_exp",
                            children=[
                                html.Img(
                                    className="contratos",
                                    src='data:image/png;base64,{}'.format(encoded_image.decode()))
                            ]
                        ),
                    ]
                ),
                html.Div(
                    className="contenedor_externo",
                    children=[
                        html.Div(
                            className="contenedor_titulos",
                            children=[
                                html.H4(
                                    className="titulos",
                                    children="Contratos celebrados por departamento"
                                )
                            ]
                        ),
                        html.Div(
                            className="contenedor_textos_aclaratorios",
                            children=[
                                dcc.Markdown(
                                    className="textos_aclaratorios",
                                    children="""El siguiente mapa interactivo de Colombia muestra el valor de los contratos celebrados por cada departamento. Los colores  permiten diferenciar el valor total de los contratos, se mostrarán en rojo los departamentos con un menor valor de contratación y en azul aquellos que tengan un mayor volumen. Fuente: [SECOP Integrado](https://www.datos.gov.co/Gastos-Gubernamentales/SECOP-Integrado/rpmr-utcd)"""
                                ),
                                dcc.Markdown(
                                    className="instrucciones",
                                    children="""Instrucciones:  el mapa muestra por defecto la información de la contratación para Colombia, si desea ver el estado de la contratación de una deparatmento en específico,  haga clic encima del departamento seleccionado y vea como la tabla de debajo de abajo se actualiza con información de acuerdo a la selección hecha. Para ver en detalle la información de San Andrés y Providencia puede hacer acercarse en el mapa usando el mouse."""
                                )
                            ]
                        ),
                        html.Div(
                            className="contenedor_graficas",
                            children=[
                                dcc.Graph(
                                    id="mapbox_contratos",
                                    figure=mapa_contratos)
                            ]
                        ),
                        html.Div(
                            className="contenedor_tablas",
                            children=[
                                dash_table.DataTable(
                                    id="tabla_dinamica_contratos",
                                    columns=[{'id': 'departamento', 'name': 'Departamento', 'type': 'text'},
                                            {'id': 'nombre_entidad', 'name': 'Entidad', 'type': 'text'},
                                            {'id': 'nombre_contratista',
                                            'name': 'Contratista', 'type': 'text'},
                                            {'id': 'conteo', 'name': 'Cantidad',
                                            'type': 'numeric'},
                                            {'id': 'promedio_contrato', 'name': 'Promedio Contratos', 'type': 'numeric', 'format': FormatTemplate.money(0)}],
                                    data=datos_contratos_entidad[[
                                        "departamento", "nombre_entidad", "nombre_contratista", "conteo", "promedio_contrato"]].to_dict("records"),
                                    style_cell_conditional=[{'if': {"column_id": "departamento"}, "width": "10%"},
                                                            {'if': {"column_id": "nombre_entidad"}, "width": "40%"},
                                                            {'if': {"column_id": "nombre_contratista"}, "width": "20%"},
                                                            {'if': {'column_id': 'conteo'}, 'width': "10%", "textAlign": "center"},
                                                            {'if': {'column_id': 'promedio_contrato'}, 'width': "20%"}],
                                    fixed_rows={'headers': True, 'data': 0},
                                    filter_action="native",
                                    sort_action="native",
                                    sort_mode='multi',
                                    style_cell={"font-family": "Work Sans", "fontSize": 13, "textAlign": "left", "color": "#004884"},
                                    style_data={'height': 'auto', 'whiteSpace': 'normal'},
                                    style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F2F2F2'}],
                                    style_table={"height": "400px"},
                                    style_header={'backgroundColor': "#004884", 'fontWeight': 'bold', "color": "#F1F1F1"},
                                    style_as_list_view=True,
                                    css=[{'selector': '.first-page, .current-page, .last-page, .page-number, .next-page, .previous-page, .page-number', 'rule': 'color: #004884'}]                                   
                                )
                            ]
                        )
                    ]
                ),
                html.Div(
                    className="contenedor_externo",
                    children=[
                        html.Div(
                            className="contenedor_titulos",
                            children=[
                                html.H4(
                                    className="titulos",
                                    children="Cantidad de contratos celebrados por modalidad (Top 10)"
                                )
                            ]
                        ),
                        html.Div(
                            className="contenedor_textos_aclaratorios",
                            children=[
                                dcc.Markdown(
                                    className="textos_aclaratorios",
                                    children="""La siguiente gráfica interactiva muestra cuántos contratos se han otorgado por modalidad. La modalidad identifica cual es el servicio prestado a través de un contrato. Esta información permite ver cuáles son las modalidad más comunes de contratación a nivel nacional. Fuente: [SECOP Integrado](https://www.datos.gov.co/Gastos-Gubernamentales/SECOP-Integrado/rpmr-utcd)"""
                                ),
                                dcc.Markdown(
                                    className="instrucciones",
                                    children="""Instrucciones:  la gráfica muestra por defecto la información de contratos por modalidad. En esta gráfica interactiva usted puede seleccionar el área que quiere ver, también puede volver a la visualización inicial dando clic en el icono con la “Casa” ubicado en la parte superior derecha del gráfico."""
                                )
                            ]
                        ),
                        html.Div(
                            className="contenedor_graficas",
                            children=[
                                dcc.Graph(id="example-graph-2",
                                    figure=go.Figure(data=contratos_objeto,
                                                    layout=go.Layout(margin=go.layout.Margin(l=50, r=50, t=50, b=50, pad=2),
                                                                        legend=go.layout.Legend(orientation="h",
                                                                        xanchor = "center",
                                                                        yanchor="top",
                                                                        x = 0.5)))
                                )
                            ]
                        )
                    ]
                ),
                html.Div(
                    className="contenedor_externo",
                    children=[
                        html.Div(
                            className="contenedor_titulos",
                            children=[
                                html.H4(
                                    className="titulos",
                                    children="Cantidad de contratos celebrados por tipo de contratación (Top 10)"
                                )
                            ]
                        ),
                        html.Div(
                            className="contenedor_textos_aclaratorios",
                            children=[
                                dcc.Markdown(
                                    className="textos_aclaratorios",
                                    children="""Existen diferentes formas en las cuales un contrato puede ser otorgado. Los tipos de contratación son mostrados en la siguiente gráfica y permiten ver cómo funcionan los procesos de compra pública en Colombia. Fuente: [SECOP Integrado](https://www.datos.gov.co/Gastos-Gubernamentales/SECOP-Integrado/rpmr-utcd)"""
                                ),
                                dcc.Markdown(
                                    className="instrucciones",
                                    children="""Instrucciones:  la gráfica muestra por defecto la información de contratos por tipo de contratación. Si desea ver la información e una modalidad en específico, haga clic encima de cada modalidad y vea cómo la gráfica se actualiza. Si desea ver información de otra modalidad, haga clic y podrá comparar los resultados."""
                                )
                            ]
                        ),
                        html.Div(
                            className="contenedor_graficas",
                            children=[
                                dcc.Graph(id="example-graph-2",
                                    figure=go.Figure(data=contratos_modalidad,
                                                    layout=go.Layout(margin=go.layout.Margin(l=50, r=50, t=50, b=50, pad=2),
                                                                        legend=go.layout.Legend(orientation="h", 
                                                                        xanchor = "center",
                                                                        x = 0.5)))
                                )
                            ]
                        ),
                        html.Div(
                            className="contenedor_textos_aclaratorios",
                            children=[
                                dcc.Markdown(
                                    className="textos_aclaratorios_opcionales",
                                    children="""Elija la categoría de su preferencia y/o interés haciendo clic sobre el nombre."""
                                )
                            ]
                        )
                    ]
                )
            ]
        )

def sanciones():
    return html.Div(
            className="body",
            children=[
                html.Div(
                    className="contenedor_externo_exp",
                    children=[
                        html.Div(
                            className="contenedor_graficas_izquierda",
                            children=[
                                html.Div(
                                    className="contenedor_textos_externos",
                                    children=[
                                        dcc.Markdown(
                                            className="textos_aclaratorios_exp",
                                            children="""En esta sección podrá encontrar información asociada a las sanciones impuestas a los contratistas a nivel nacional. Su propósito es poder mostrar de una manera sencilla por cada uno de los departamentos el valor total de las sanciones y su valor relativo, es decir dividiendo las sanciones por el valor total de contratación. El periodo de tiempo para el registro de las sanciones empieza desde el 30 de Mayo de 2017."""
                                        )
                                    ]
                                )
                            ]
                        ),
                        html.Div(
                            className="contenedor_graficas_derecha",
                            children=[
                                html.Img(
                                    className="sanciones",
                                    src='data:image/png;base64,{}'.format(encoded_sanciones_image.decode()))
                            ]
                        ),
                    ]
                ),
                html.Div(
                    className="contenedor_externo",
                    children=[
                        html.Div(
                            className="contenedor_titulos",
                            children=[
                                html.H4(
                                    className="titulos",
                                    children="Contratos sancionados por departamento"
                                )
                            ]
                        ),
                        html.Div(
                            className="contenedor_textos_aclaratorios",
                            children=[
                                dcc.Markdown(
                                    className="textos_aclaratorios",
                                    children="""En esta mapa de Colombia se muestra la cantidad total de los contratos sancionados. Si da un clic encima de cada departamento, la tabla de abajo le permitirá ver información específica, mostrando el valor, la entidad y el contratista. También podrá seleccionar los departamentos de su preferencia o verlo a nivel nacional. En la escala de colores podrá ver la mayor concentración en términos del monto total de sanciones. Un color rojo identificará valores más altos y en azul se mostrarán los más bajos. Fuente: [SECOP Sanciones](https://www.datos.gov.co/Gastos-Gubernamentales/Multas-y-Sanciones-SECOP-I/4n4q-k399)"""
                                ),
                                dcc.Markdown(
                                    className="instrucciones",
                                    children="""Instrucciones:  el mapa muestra por defecto la información de las sanciones en todos el país, si desea ver el estado de la contratación de una departamento en específico,  haga clic encima del departamento seleccionado y vea cómo la tabla de debajo de abajo se actualiza con información de acuerdo a la selección hecha. Para ver en detalle la información de San Andrés y Providencia puede hacer acercarse en el mapa usando el mouse."""
                                )
                            ]
                        ),
                        html.Div(
                            className="contenedor_graficas",
                            children=[
                                dcc.Graph(
                                    id="mapbox_sanciones",
                                    figure=mapa_sanciones
                                )
                            ]
                        ),
                        html.Div(
                            className="contenedor_tablas",
                            children=[
                                dash_table.DataTable(
                                    id="tabla_dinamica_sanciones",
                                    columns=[{'id': 'departamento', 'name': 'Departamento', 'type': 'text'},
                                            {'id': 'nombre_entidad', 'name': 'Nombre Entidad', 'type': 'text'},
                                            {'id': 'nit_entidad', 'name': 'NIT Entidad', 'type': 'text'},
                                            {'id': 'conteo', 'name': 'Cantidad', 'type': 'numeric'},
                                            {'id': 'promedio_sancion', 'name': 'Promedio Sanción', 'type': 'numeric', 'format': FormatTemplate.money(0)}],
                                    data=datos_sancion_contratante[["departamento", "nombre_entidad", "nit_entidad", "conteo", "promedio_sancion"]].to_dict("records"),
                                    style_cell_conditional=[{'if': {"column_id": "departamento"}, "width": "10%"},
                                                            {'if': {'column_id': 'nombre_entidad'}, 'width': "40%"},
                                                            {'if': {'column_id': 'nit_entidad'}, 'width': "10%"},
                                                            {'if': {'column_id': 'conteo'}, 'width': "5%", "textAlign": "center"},
                                                            {'if': {'column_id': 'promedio_sancion'}, 'width': "10%"}],
                                    fixed_rows={'headers': True, 'data': 0},
                                    filter_action="native",
                                    sort_action="native",
                                    sort_mode='multi',
                                    style_cell={"font-family": "Work Sans", "fontSize": 13, "textAlign": "left", "color": "#004884"},
                                    style_data={'height': 'auto', 'whiteSpace': 'normal'},
                                    style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F2F2F2'}],
                                    style_table={"height": "400px"},
                                    style_header={'backgroundColor': "#004884", 'fontWeight': 'bold', "color": "#F1F1F1"},
                                    style_as_list_view=True,
                                    css=[{'selector': '.first-page, .current-page, .last-page, .page-number, .next-page, .previous-page, .page-number', 'rule': 'color: #004884'}]
                                )
                            ]
                        )
                    ]
                ),
                html.Div(
                    className="contenedor_externo",
                    children=[
                        html.Div(
                            className="contenedor_titulos",
                            children=[
                                html.H4(
                                    className="titulos",
                                    children="Cantidad de contratos sancionados - Bogotá"
                                )
                            ]
                        ),
                        html.Div(
                            className="contenedor_textos_aclaratorios",
                            children=[
                                dcc.Markdown(
                                    className="textos_aclaratorios",
                                    children="""En esta gráfica se muestra información específica para Bogotá, teniendo en cuenta el valor de las sanciones aplicadas. Se ha excluido a Bogotá de la medición anterior, ya que Bogotá tiene el valor más alto en términos de contratos sancionados. Fuente: [SECOP Sanciones](https://www.datos.gov.co/Gastos-Gubernamentales/Multas-y-Sanciones-SECOP-I/4n4q-k399)"""
                                ),
                                dcc.Markdown(
                                    className="instrucciones",
                                    children="""Instrucciones: la gráfica de burbujas muestra toda la información asociada a los procesos de contratación  en Bogotá, para ver un valor en específico puede dar clic sobre una burbuja. También puede seleccionar el área de la gráfica que quiere ver en detalle para hacer “Zoom”, si desea volver a la gráfica original puede dar clic sobre el botón con una “Casa” ubicado en la parte superior derecha del gráfico."""
                                )
                            ]
                        ),
                        html.Div(
                            className="contenedor_graficas",
                            children=[
                                dcc.Graph(id="example-graph-3",
                                        figure=go.Figure(data=sanciones_bogota,
                                                        layout=go.Layout(xaxis_title="Cantidad de contratos sancionados por entidad",
                                                                        yaxis_title="Valor promedio de la sanción por contratista",
                                                                        margin=go.layout.Margin(
                                                                            l=50, r=50, t=5, b=5, pad=1),
                                                                        xaxis_type="log",
                                                                        yaxis_type="log",
                                                                        legend=go.layout.Legend(orientation="h",
                                                                        xanchor = "center",
                                                                        x = 0.5))))
                            ]
                        )
                    ]
                ),
                html.Div(
                    className="contenedor_externo",
                    children=[
                        html.Div(
                            className="contenedor_titulos",
                            children=[
                                html.H4(
                                    className="titulos",
                                    children="Cantidad de contratos sancionados y monto de sanción por contratante y contratista"
                                )
                            ]
                        ),
                        html.Div(
                            className="contenedor_textos_aclaratorios",
                            children=[
                                dcc.Markdown(
                                    className="textos_aclaratorios",
                                    children="""Se muestra el valor promedio de sanciones impuestas por departamento. Puede interactuar con el mapa seleccionado el departamento de su preferencia y viendo el detalle en la tabla inferior. La escala de colores al lado derecho del mapa permite diferenciar el valor de las sanciones. Fuente: [SECOP Sanciones](https://www.datos.gov.co/Gastos-Gubernamentales/Multas-y-Sanciones-SECOP-I/4n4q-k399)"""
                                )
                            ]
                        ),
                        html.Div(
                            className="contenedor_tablas",
                            children=[
                                dash_table.DataTable(
                                    id="tabla_sancionados_contratista",
                                    columns=[{'id': 'departamento', 'name': 'Departamento', 'type': 'text'},
                                            {'id': 'entidad', 'name': 'Nombre Entidad', 'type': 'text'},
                                            {'id': 'nombre_contratista', 'name': 'Contratista', 'type': 'text'},
                                            {'id': 'documento_contratista', 'name': 'NIT Contratista', 'type': 'text'},
                                            {'id': 'conteo', 'name': 'Cantidad', 'type': 'numeric'},
                                            {'id': 'promedio_sancion', 'name': 'Promedio Sanción', 'type': 'numeric', 'format': FormatTemplate.money(0)}],
                                    data=datos_sancion_contratista[["departamento", "entidad", "nombre_contratista", "documento_contratista", "conteo", "promedio_sancion"]].to_dict("records"),
                                    style_cell_conditional=[{'if': {"column_id": "departamento"}, "width": "10%"},
                                                            {'if': {'column_id': 'nombre_entidad'}, 'width': "40%"},
                                                            {'if': {'column_id': 'nit_entidad'}, 'width': "10%"},
                                                            {'if': {'column_id': 'conteo'}, 'width': "5%", "textAlign": "center"},
                                                            {'if': {'column_id': 'promedio_sancion'}, 'width': "20%"}],
                                    fixed_rows={'headers': True, 'data': 0},
                                    filter_action="native",
                                    sort_action="native",
                                    sort_mode='multi',
                                    style_cell={"font-family": "Work Sans", "fontSize": 13, "textAlign": "left", "color": "#004884"},
                                    style_data={'height': 'auto', 'whiteSpace': 'normal'},
                                    style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F2F2F2'}],
                                    style_table={"height": "400px"},
                                    style_header={'backgroundColor': "#004884", 'fontWeight': 'bold', "color": "#F1F1F1"},
                                    style_as_list_view=True,
                                    css=[{'selector': '.first-page, .current-page, .last-page, .page-number, .next-page, .previous-page, .page-number', 'rule': 'color: #004884'}]
                                )
                            ]
                        )
                    ]
                ),
                html.Div(
                    className="contenedor_externo",
                    children=[
                        html.Div(
                            className="contenedor_titulos",
                            children=[
                                html.H4(
                                    className="titulos",
                                    children="Valor promedio de sanción por departamento"
                                )
                            ]
                        ),
                        html.Div(
                            className="contenedor_textos_aclaratorios",
                            children=[
                                dcc.Markdown(
                                    className="textos_aclaratorios",
                                    children="""Se muestra el valor promedio de sanciones impuestas por departamento. Puede interactuar con el mapa seleccionado el departamento de su preferencia y viendo el detalle en la tabla inferior. La escala de colores al lado derecho del mapa permite diferenciar el valor de las sanciones. Fuente: [SECOP Sanciones](https://www.datos.gov.co/Gastos-Gubernamentales/Multas-y-Sanciones-SECOP-I/4n4q-k399)"""
                                ),
                                dcc.Markdown(
                                    className="instrucciones",
                                    children="""Instrucciones:  el mapa muestra por defecto la información de las sanciones en todos el país, si desea ver el estado de la contratación de una departamento en específico,  haga clic encima del departamento seleccionado y vea cómo la tabla de debajo de abajo se actualiza con información de acuerdo a la selección hecha. Para ver en detalle la información de San Andrés y Providencia puede hacer acercarse en el mapa usando el mouse."""
                                )
                            ]
                        ),
                        html.Div(
                            className="contenedor_graficas",
                            children=[
                                dcc.Graph(
                                    id="mapbox_sanciones_monto",
                                    figure=mapa_sanciones_monto
                                )
                            ]
                        )
                    ]
                )
        ]
    )

def alertas():
    return html.Div(
            className="body",
                children=[
                    html.Div(
                        className="contenedor_externo_exp",
                        children=[
                            html.Div(
                                className="contenedor_graficas_izquierda",
                                children=[
                                    html.Div(
                                        className="contenedor_textos_externos_izq2",
                                        children=[
                                            dcc.Markdown(
                                                children='''En esta sección, se analizan los resultados de la Transparencia en la Contratación Pública, tomando  conjuntos de datos abiertos del SECOP y el PIDA (Plan interamericano de datos abiertos) y generando de manera automática los indicadores del Sistema de Compra y Contratación Pública. Estos resultados pueden ser tomados como alertas para entender el desarrollo de la Contratación Pública en Colombia.''',
                                                className="textos_aclaratorios_exp"
                                            )
                                        ]
                                    )
                                ]
                            ),
                            html.Div(
                                className="contenedor_graficas_derecha",
                                children=[
                                    html.Img(
                                        className="alertas",
                                        src='data:image/png;base64,{}'.format(encoded_alerts_image.decode()))
                                ]
                            )
                        ]
                    ),
                    html.Div(
                        className="contenedor_externo",
                        children=[
                            html.Div(
                                className="contenedor_titulos",
                                children=[
                                    html.H4(
                                        className="titulos",
                                        children="Proporción de contratistas nuevos"
                                    )
                                ]
                            ),
                            html.Div(
                                className="contenedor_textos_aclaratorios",
                                children=[
                                    dcc.Markdown(
                                        children="""En esta tabla se muestra la cantidad de proveedores nuevos contratados frente a la totalidad de las los contratos celebrados por cada entidad. Mostrando las 20 entidades con la menor cantidad de contratistas nuevos. Si la tabla aparece vacía es porque no hay datos para mostrar. Fuente: [SECOP Integrado](https://www.datos.gov.co/Gastos-Gubernamentales/SECOP-Integrado/rpmr-utcd). Tenga en cuenta en que sólo se generarán resultados si existen alertas para el críterio mostrado.""",
                                        className="textos_aclaratorios"
                                    )
                                ]
                            ),
                            html.Div(
                                className="contenedor_tablas",
                                children=[
                                    dash_table.DataTable(
                                        id="tabla_p2",
                                        data=datos_p2.to_dict("records"),
                                        columns=[{'id': 'entidad', 'name': 'Entidad', 'type': 'text'},
                                                {'id': 'activos', 'name': 'Contratos Activos', 'type': 'numeric'},
                                                {'id': 'nuevos', 'name': 'Contratos Nuevos', 'type': 'numeric'},
                                                {'id': 'proporcion', 'name': 'Proporción Nuevos (%)', 'type': 'numeric'}],
                                        style_cell_conditional=[{'if': {"column_id": "entidad"}, "width": "30%"},
                                                            {'if': {'column_id': 'activos'}, 'width': "15%", "textAlign": "center"},
                                                            {'if': {'column_id': 'nuevos'}, 'width': "15%", "textAlign": "center"},
                                                            {'if': {'column_id': 'proporcion'}, 'width': "15%", "textAlign": "center"}],
                                        fixed_rows={'headers': True, 'data': 0},
                                        filter_action="native",
                                        sort_action="native",
                                        sort_mode='multi',
                                        style_cell={"font-family": "Work Sans", "fontSize": 13, "textAlign": "left", "color": "#004884"},
                                        style_data={'height': 'auto', 'whiteSpace': 'normal'},
                                        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F2F2F2'}],
                                        style_table={"height": "400px"},
                                        style_header={'backgroundColor': "#F42F63", 'fontWeight': 'bold', "color": "white"},
                                        style_as_list_view=True,
                                        css=[{'selector': '.first-page, .current-page, .last-page, .page-number, .next-page, .previous-page, .page-number', 'rule': 'color: #004884'}]
                                    )
                                ]
                            )
                        ]
                    ),
                    html.Div(
                        className="contenedor_externo",
                        children=[
                            html.Div(
                                className="contenedor_titulos",
                                children=[
                                    html.H4(
                                        className="titulos",
                                        children="Concentración del valor de los contratos por entidad"
                                    )
                                ]
                            ),
                            html.Div(
                                children=[
                                    html.Div(
                                        className="contenedor_graficas_izquierda",
                                        children=[
                                            html.Div(
                                                className="contenedor_textos_externos",
                                                children=[
                                                    dcc.Markdown(
                                                        children="""En la siguiente tabla se muestra por entidad, la distribución del valor total de las contrataciones entre los diferentes proveedores. Si por ejemplo el valor total de la contratación es distribuido en todos los contratistas por igual, el indicador será 0, si por el contrario el valor total de contratación está en un único contratista el indicador será 1. Si la tabla aparece vacía es porque no hay datos para mostrar. Fuente: [SECOP Integrado](https://www.datos.gov.co/Gastos-Gubernamentales/SECOP-Integrado/rpmr-utcd). Tenga en cuenta en que sólo se generarán resultados si existen alertas para el críterio mostrado.""",
                                                        className="textos_aclaratorios"
                                                    )
                                                ]
                                            )
                                        ]
                                    ),
                                    html.Div(
                                        className="contenedor_graficas_derecha",
                                        children=[
                                            dash_table.DataTable(
                                                id="tabla_p3",
                                                columns=[{'id': 'entidad', 'name': 'Entidad', 'type': 'text'},
                                                        {'id': 'gini', 'name': 'Concentración', 'type': 'numeric'}],
                                                data=datos_p3.to_dict("records"),
                                                style_cell_conditional=[{'if': {"column_id": "entidad"}, "width": "80%", "textAlign": "left"},
                                                                        {'if': {'column_id': 'gini'}, 'width': "20%", "textAlign": "center"}],
                                                fixed_rows={'headers': True, 'data': 0},
                                                filter_action="native",
                                                sort_action="native",
                                                sort_mode='multi',
                                                style_cell={"font-family": "Work Sans", "fontSize": 13, "textAlign": "left", "color": "#004884"},
                                                style_data={'height': 'auto', 'whiteSpace': 'normal'},
                                                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F2F2F2'}],
                                                style_header={'backgroundColor': "#F42F63", 'fontWeight': 'bold', "color": "white"},
                                                style_as_list_view=True,
                                                css=[{'selector': '.first-page, .current-page, .last-page, .page-number, .next-page, .previous-page, .page-number', 'rule': 'color: #004884'}]
                                            )
                                        ]
                                    )
                                ]
                            )
                        ]
                    ),
                    html.Div(
                        className="contenedor_externo",
                        children=[
                            html.Div(
                                className="contenedor_titulos",
                                children=[
                                    html.H4(
                                        className="titulos",
                                        children="Contratos adjudicados a proponentes plurales"
                                    )
                                ]
                            ),
                            html.Div(
                                className="contenedor_textos_aclaratorios",
                                children=[
                                    dcc.Markdown(
                                        children='''*En esta tabla podrá ver como se desarrollan los procesos de compra pública a través Consorcios o Uniones Temporales,  mostrando su proporción contra el total de las contrataciones hechas. Se evalúa este indicador para todas las entidades y se muestran en la tabla aquellas con una mayor porcentaje de contratos hechos a través de Consorcios y Uniones Temporales. Si la tabla aparece vacía es porque no hay datos para mostrar. Fuente: [SECOP II Contratos](). Tenga en cuenta en que sólo se generarán resultados si existen alertas para el críterio mostrado.''',
                                        className="textos_aclaratorios"
                                    )
                                ]
                            ),
                            html.Div(
                                className="contenedor_tablas",
                                children=[
                                    dash_table.DataTable(
                                        id="tabla_p4",
                                        columns=[{'id': 'entidad', 'name': 'Entidad', 'type': 'text'},
                                                {'id': 'ano', 'name': 'Año', 'type': 'numeric'},
                                                {'id': 'adjudicados', 'name': 'Adjudicados', 'type': 'numeric'},
                                                {'id': 'valor_adjudicado', 'name': 'Valor Adjudicado', 'type': 'numeric', 'format': FormatTemplate.money(0)},
                                                {'id': 'plurales', 'name': 'Contratos Entidades Plurales', 'type': 'numeric'},
                                                {'id': 'prop_plurales', 'name': 'Participación Plurales (%)', 'type': 'numeric'},
                                                {'id': 'prop_valor_plurales', 'name': 'Participación Valor Contratos Plurales (%)', 'type': 'numeric'}],
                                        data=datos_p4.to_dict("records"),
                                        style_cell_conditional=[{'if': {"column_id": "entidad"}, "width": "30%"},
                                                                {'if': {'column_id': 'ano'}, 'width': "5%", "textAlign": "center"},
                                                                {'if': {'column_id': 'adjudicados'}, 'width': "10%", "textAlign": "center"},
                                                                {'if': {'column_id': 'valor_adjudicado'}, 'width': "10%"},
                                                                {'if': {'column_id': 'plurales'}, 'width': "12%", "textAlign": "center"},
                                                                {'if': {'column_id': 'prop_plurales'}, 'width': "15%", "textAlign": "center"},
                                                                {'if': {'column_id': 'prop_valor_plurales'}, 'width': "18%", "textAlign": "center"}],
                                        fixed_rows={'headers': True, 'data': 0},
                                        filter_action="native",
                                        sort_action="native",
                                        sort_mode='multi',
                                        style_cell={"font-family": "Work Sans", "fontSize": 13, "textAlign": "left", "color": "#004884"},
                                        style_data={'height': 'auto', 'whiteSpace': 'normal'},
                                        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F2F2F2'}],
                                        style_header={'backgroundColor': "#F42F63", 'fontWeight': 'bold', "color": "white"},
                                        style_as_list_view=True,
                                        css=[{'selector': '.first-page, .current-page, .last-page, .page-number, .next-page, .previous-page, .page-number', 'rule': 'color: #004884'}]
                                    )
                                ]
                            )
                        ]
                    ),
                    html.Div(
                        className="contenedor_externo",
                        children=[
                            html.Div(
                                className="contenedor_titulos",
                                children=[
                                    html.H4(
                                        className="titulos",
                                        children="Contratos asignados de forma no competitiva"
                                    )
                                ]
                            ),
                            html.Div(
                                className="contenedor_textos_aclaratorios",
                                children=[
                                    dcc.Markdown(
                                        children='''En esta tabla se muestran las entidades con mayor porcentaje de contratos adjudicados en procesos no competitivos excluyendo los interadministrativos y prestación de servicios profesionales. Con el objetivo de asegurar la transparencia en la contratación pública, siempre se busca que los procesos de contratación garanticen las condiciones para la participación de varios proponentes. Si la tabla aparece vacía es porque no hay datos para mostrar. Fuente [SECOP II Contratos](https://www.datos.gov.co/Gastos-Gubernamentales/SECOP-II-Contratos/gnxj-bape) y [SECOP II Procesos](https://www.datos.gov.co/Gastos-Gubernamentales/SECOP-II-Procesos/aimg-uskh). Tenga en cuenta en que sólo se generarán resultados si existen alertas para el críterio mostrado.''',
                                        className="textos_aclaratorios"
                                    )
                                ]
                            ),
                            html.Div(
                                className="contenedor_tablas",
                                children=[
                                    dash_table.DataTable(
                                        id="tabla_p5",
                                        columns=[{'id': 'entidad', 'name': 'Entidad', 'type': 'text'},
                                                {'id': 'ejecutados', 'name': 'Contratos Ejecutados', 'type': 'numeric'},
                                                {'id': 'especificos', 'name': 'Contratos Específicos', 'type': 'numeric'},
                                                {'id': 'adjudicados_no_competitivos', 'name': 'Contratos No Competitivos (%)', 'type': 'numeric'}],
                                        data=datos_p5.to_dict("records"),
                                        style_cell_conditional=[{'if': {"column_id": "entidad"}, "width": "55%"},
                                                                {'if': {'column_id': 'ejecutados'}, 'width': "15%", "textAlign": "center"},
                                                                {'if': {'column_id': 'especificos'},'width': "15%", "textAlign": "center"},
                                                                {'if': {'column_id': 'adjudicados_no_competitivos'}, 'width': "15%", "textAlign": "center"}],
                                        fixed_rows={'headers': True, 'data': 0},
                                        filter_action="native",
                                        sort_action="native",
                                        sort_mode='multi',
                                        style_cell={"font-family": "Work Sans", "fontSize": 13, "textAlign": "left", "color": "#004884"},
                                        style_data={'height': 'auto', 'whiteSpace': 'normal'},
                                        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F2F2F2'}],
                                        style_header={'backgroundColor': "#F42F63", 'fontWeight': 'bold', "color": "white"},
                                        style_as_list_view=True,
                                        css=[{'selector': '.first-page, .current-page, .last-page, .page-number, .next-page, .previous-page, .page-number', 'rule': 'color: #004884'}]
                                    )
                                ]
                            )
                        ]
                    ),
                    html.Div(
                        children=[
                            html.Div(
                                className="contenedor_externo",
                                children=[
                                    html.Div(
                                        className="contenedor_textos_aclaratorios",
                                        children=[
                                            dcc.Markdown(
                                                children='''Muestra la cantidad de entidades públicas que no hacen uso de la plataforma del SECOP para realizar sus procesos de compra pública o que no publica su plan de adquisiciones.  El Sistema Electrónico de Contratación Pública (SECOP) es una plataforma que permite a los compradores y proveedores hacer los procesos de contratación pública en línea, promoviendo la transparencia en los procesos de contratación.  En las siguientes tablas interactivas, podrá filtrar por departamento para poder ver las entidades. Si la tabla aparece vacía es porque no hay datos para mostrar.''',
                                                className="textos_aclaratorios"
                                            ),
                                            dcc.Markdown(
                                                children='''Instrucciones:  las tablas muestra información de todos las entidades del país, si desea filtrar por departamento, debe seleccionar el departamento en el menú desplegable y automáticamente se actualizarán las tablas de entidades que no usan SECOP y que no publican el Plan de Adquisiciones por departamento. ''',
                                                className="instrucciones"
                                            )
                                        ]
                                    ),
                                    html.Div(
                                        className="contenedor_selectores",
                                        children=[
                                            dcc.Dropdown(
                                                id="opt",
                                                options=opts,
                                                value=opts[1]["value"],
                                                className="selector_departamento"
                                            )
                                        ]
                                    ),
                                    html.Div(
                                        className="contenedor_graficas_izquierda_tablas",
                                        children=[
                                            html.Div(
                                                className="contenedor_externo_interno",
                                                children=[
                                                    html.Div(
                                                        className="contenedor_titulos",
                                                        children=[
                                                            dcc.Markdown(
                                                                className="titulos",
                                                                children="""Entidades que no usan SECOP"""
                                                            )
                                                        ]
                                                    ),
                                                    html.Div(
                                                        className="contenedor_textos_aclaratorios",
                                                        children=[
                                                            dcc.Markdown(
                                                                children='''Fuentes: [SECOP Integrado](https://www.datos.gov.co/Gastos-Gubernamentales/SECOP-Integrado/rpmr-utcd) y [Entidades Registradas en el Sistema CHIP](https://www.datos.gov.co/Hacienda-y-Cr-dito-P-blico/Inventario-De-Entidades-P-blicas-Registradas-En-El/fzc7-w78v)''',
                                                                className="textos_aclaratorios_medianos"
                                                            )
                                                        ]
                                                    ),
                                                    html.Div(
                                                        className="contenedor_tablas_medianas",
                                                        children=[
                                                            dash_table.DataTable(
                                                                id="tabla_p6",
                                                                columns=[{'id': 'entidad', 'name': 'Entidad', 'type': 'text'},
                                                                    {'id': 'departamento', 'name': 'Departamento', 'type': 'text'}],
                                                                data=datos_p6.to_dict("records"),
                                                                style_cell_conditional=[{'if': {"column_id": "entidad"}, "width": "10%"},
                                                                        {'if': {'column_id': 'departamento'}, 'width': "10%"}],
                                                                fixed_rows={'headers': True, 'data': 0},
                                                                filter_action="native",
                                                                sort_action="native",
                                                                sort_mode='multi',
                                                                style_cell={"font-family": "Work Sans", "fontSize": 13, "textAlign": "left", "color": "#004884"},
                                                                style_data={'height': 'auto', 'whiteSpace': 'normal', "border": "0px"},
                                                                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F2F2F2'}],
                                                                style_table={"height": "400px"},
                                                                style_header={'backgroundColor': "#F42F63", 'fontWeight': 'bold', "color": "white"},
                                                                style_as_list_view=True,
                                                                css=[{'selector': '.first-page, .current-page, .last-page, .page-number, .next-page, .previous-page, .page-number', 'rule': 'color: #004884'}]
                                                            )
                                                        ]
                                                    )
                                                ]
                                            )
                                        ]
                                    ),
                                    html.Div(
                                        className="contenedor_graficas_derecha_tablas",
                                        children=[
                                            html.Div(
                                                className="contenedor_externo_interno",
                                                children=[
                                                    html.Div(
                                                        className="contenedor_titulos",
                                                        children=[
                                                            html.H4(
                                                                className="titulos",
                                                                children="Entidades que no publican Plan de Adquisiciones en SECOP"
                                                            )
                                                        ]
                                                    ),
                                                    html.Div(
                                                        className="contenedor_textos_aclaratorios",
                                                        children=[
                                                            dcc.Markdown(
                                                                children='''Fuentes: [Entidades Registradas en el Sistema CHIP](https://www.datos.gov.co/Hacienda-y-Cr-dito-P-blico/Inventario-De-Entidades-P-blicas-Registradas-En-El/fzc7-w78v) y [Plan Anual de Adquisiciones](https://www.datos.gov.co/Gastos-Gubernamentales/Plan-Anual-de-Adquisiciones-SECOP-II/vfek-dafh)''',
                                                                className="textos_aclaratorios_medianos"
                                                            )
                                                        ]
                                                    ),
                                                    html.Div(
                                                        className="contenedor_tablas_medianas",
                                                        children=[
                                                            dash_table.DataTable(
                                                                id="tabla_p7",
                                                                columns=[{'id': 'entidad', 'name': 'Entidad', 'type': 'text'},
                                                                    {'id': 'departamento', 'name': 'Departamento', 'type': 'text'}],
                                                                data=datos_p7.to_dict("records"),
                                                                style_cell_conditional=[{'if': {"column_id": "entidad"}, "width": "10%"},
                                                                        {'if': {'column_id': 'departamento'}, 'width': "10%"}],
                                                                fixed_rows={'headers': True, 'data': 0},
                                                                filter_action="native",
                                                                sort_action="native",
                                                                sort_mode='multi',
                                                                style_cell={"font-family": "Work Sans", "fontSize": 13, "textAlign": "left", "color": "#004884"},
                                                                style_data={'height': 'auto', 'whiteSpace': 'normal', "border": "0px"},
                                                                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F2F2F2'}],
                                                                style_table={"height": "400px"},
                                                                style_header={'backgroundColor': "#F42F63", 'fontWeight': 'bold', "color": "white"},
                                                                style_as_list_view=True,
                                                                css=[{'selector': '.first-page, .current-page, .last-page, .page-number, .next-page, .previous-page, .page-number', 'rule': 'color: #004884'}]
                                                            )
                                                        ]
                                                    )
                                                ]
                                            )
                                        ]
                                    )
                                ]
                            )
                    ]
                )
            ]
        )

@app.callback(dash.dependencies.Output('contenido-territorio', 'children'),
              [dash.dependencies.Input('tab-territorio', 'value')])
def render_content(tab):
    if tab == "contratos":
        return contratos()

    elif tab == "sanciones":
        return sanciones()

    elif tab == "alertas":
        return alertas()

@app.callback(dash.dependencies.Output('contenido-subtab-territorio', 'children'),
              [dash.dependencies.Input('subtab-territorio', 'value')])
def render_content(tab):
    if tab == "contratos":
        return contratos()

    elif tab == "sanciones":
        return sanciones()

@app.callback([dash.dependencies.Output(component_id="tabla_dinamica_contratos", component_property="data"),
               dash.dependencies.Output(component_id="tabla_dinamica_contratos", component_property="columns")],
              [dash.dependencies.Input(component_id="mapbox_contratos", component_property="clickData")])
def update_table_contratos(selection):
    if selection is not None:
        point = selection["points"][0]
        data = datos_contratos_entidad[datos_contratos_entidad.departamento == point["text"]]
        data = data[["departamento", "nombre_entidad", "nombre_contratista", "conteo", "promedio_contrato"]]
        columns = [{'id': 'departamento', 'name': 'Departamento', 'type': 'text'},
                   {'id': 'nombre_entidad', 'name': 'Entidad', 'type': 'text'},
                   {'id': 'nombre_contratista', 'name': 'Contratista', 'type': 'text'},
                   {'id': 'conteo', 'name': 'Conteo', 'type': 'numeric'},
                   {'id': 'promedio_contrato', 'name': 'Promedio Contratos', 'type': 'numeric', 'format': FormatTemplate.money(0)}]
        return data.to_dict("records"), columns


@app.callback([dash.dependencies.Output(component_id="tabla_dinamica_sanciones", component_property="data"),
               dash.dependencies.Output(component_id="tabla_dinamica_sanciones", component_property="columns")],
              [dash.dependencies.Input(component_id="mapbox_sanciones", component_property="clickData")])
def update_table_sanciones(selection):
    if selection is not None:
        point = selection["points"][0]
        data = datos_sancion_contratante[datos_sancion_contratante.departamento == point["text"]]
        data = data[["departamento", "nombre_entidad", "nit_entidad", "conteo", "promedio_sancion"]]
        columns = [{'id': 'departamento', 'name': 'Departamento', 'type': 'text'},
                   {'id': 'nombre_entidad', 'name': 'Nombre Entidad', 'type': 'text'},
                   {'id': 'nit_entidad', 'name': 'NIT Entidad', 'type': 'text'},
                   {'id': 'conteo', 'name': 'Conteo', 'type': 'numeric'},
                   {'id': 'promedio_sancion', 'name': 'Promedio Sanción', 'type': 'numeric', 'format': FormatTemplate.money(0)}]
        return data.to_dict("records"), columns

@app.callback([dash.dependencies.Output(component_id="tabla_p6", component_property="data"),
               dash.dependencies.Output(component_id="tabla_p6", component_property="columns")],
              [dash.dependencies.Input(component_id="opt", component_property="value")])
def update_table_p6(input1):
    
    data = datos_p6[datos_p6.departamento == input1]
    columns = [{'id': 'entidad', 'name': 'Entidad', 'type': 'text'},
        {'id': 'departamento', 'name': 'Departamento', 'type': 'text'}]
    return data.to_dict("records"), columns

@app.callback([dash.dependencies.Output(component_id="tabla_p7", component_property="data"),
               dash.dependencies.Output(component_id="tabla_p7", component_property="columns")],
              [dash.dependencies.Input(component_id="opt", component_property="value")])
def update_table_p7(input1):
    
    data = datos_p7[datos_p7.departamento == input1]
    columns = [{'id': 'entidad', 'name': 'Entidad', 'type': 'text'},
        {'id': 'departamento', 'name': 'Departamento', 'type': 'text'}]
    return data.to_dict("records"), columns


if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port="8051")
