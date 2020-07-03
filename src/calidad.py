import os
import requests
import base64
import math
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

external_stylesheets = ["https://fonts.googleapis.com/css?family=Montserrat&display=swap", "https://fonts.googleapis.com/css?family=Work+Sans&display=swap"]

exec(open("/var/www/modelodatosabiertos/db_credentials.sh").read())
# exec(open("db_credentials.sh").read())

db_user = MARIADB_USER
db_password = MARIADB_PASSWORD
db_host = MARIADB_HOST
db_database = MARIADB_DB

nuevos_dataset = """
        SELECT fecha_ejecucion,
        SUM(nuevo) AS nuevos,
        SUM(actualizado) AS actualizado
        FROM dataset
        GROUP BY fecha_ejecucion;
    """

nuevos_categoria = """
        SELECT
        categoria,
        fecha_ejecucion,
        SUM(actualizado) AS actualizados,
        SUM(nuevo) AS nuevos
        FROM dataset
        WHERE categoria <> ''
        GROUP BY 1, 2;
    """
    
db_connection = MariaDB_Connect(user=db_user,
                                password=db_password,
                                host=db_host,
                                database=db_database)
db_connection.connect_db()
data_nuevos = db_connection.connection.execute(nuevos_dataset).fetchall()
data_nuevos = pd.DataFrame(data_nuevos, columns=["fecha_ejecucion", "actualizados", "nuevos"])
data_categoria = db_connection.connection.execute(nuevos_categoria).fetchall()
data_categoria = pd.DataFrame(data_categoria, columns=["categoria", "fecha_ejecucion", "actualizados", "nuevos"])
db_connection.close_db()

nuevos = go.Bar(x=data_nuevos.fecha_ejecucion,
                y=data_nuevos.nuevos,
                type="bar",
                name="Conjuntos Nuevos")

actualizados = go.Bar(x=data_nuevos.fecha_ejecucion,
                    y=data_nuevos.actualizados,
                    type="bar",
                    name="Conjuntos Actualizados")

nuevos_categoria = go.Scatter(x=data_categoria.loc[data_categoria.categoria == "Ciencia, Tecnologia e Innovacion", "fecha_ejecucion"],
                            y=data_categoria.loc[data_categoria.categoria =="Ciencia, Tecnologia e Innovacion", "nuevos"],
                            name="Nuevos")

actualizados_categoria = go.Scatter(x=data_categoria.loc[data_categoria.categoria == "Ciencia, Tecnologia e Innovacion", "fecha_ejecucion"],
                                    y=data_categoria.loc[data_categoria.categoria =="Ciencia, Tecnologia e Innovacion", "actualizados"],
                                    name="Actualizados")

fig = go.Figure(data=[nuevos_categoria, actualizados_categoria])
fig_layout = go.Layout(xaxis_title="Fecha de ejecución",
                    yaxis_title="Cantidad de conjunto de datos nuevos - actualizados",
                    margin=go.layout.Margin(l=10, r=10, t=10, b=10, pad=2),
                    barmode="stack",
                    legend=go.layout.Legend(orientation="h"))

opts = data_categoria.groupby("categoria").count().index.tolist()
opts = [{"label": i, "value": i} for i in opts]
dates = data_categoria.groupby("fecha_ejecucion").count().index.tolist()
date_mark = {i: dates[i] for i in range(len(dates))}

##############################################################################
## Calidad

calidad_data = pd.read_csv("/var/www/modelodatosabiertos/src/data/Quality_Indicators.csv", sep=";", encoding="UTF-8")
# calidad_data = pd.read_csv("src/data/Quality_Indicators.csv", sep=";", encoding="UTF-8")
calidad_data.columns = ["id", "entidad", "categoria", "nombre", "Completitud",
    "Credibilidad", "Actualidad", "Trazabilidad", "Disponibilidad", "Conformidad", "Comprensibilidad", "Portabilidad",
    "Consistencia", "Exactitud"]

dimensiones = ["Completitud", "Credibilidad", "Actualidad", "Trazabilidad", "Disponibilidad", "Conformidad", "Comprensibilidad", "Portabilidad", "Consistencia", "Exactitud"]
promedios = np.average(calidad_data.iloc[:, 4:], axis=0)

radar_promedio = go.Figure(data=go.Scatterpolar(r=promedios, 
    theta=dimensiones, 
    fill='toself'))

radar_promedio.update_layout(
    polar=dict(radialaxis=dict(visible=True)),
    showlegend=False,
    margin=go.layout.Margin(l=50, r=50, t=40, b=20, pad=1),
    legend=go.layout.Legend(orientation="h", xanchor = "center", x = 0.5, y=-0.2)
)

calidad_categoria = calidad_data.groupby(["categoria"], as_index=False).mean()

radar_categoria = go.Figure()

radar_categoria.add_trace(
    go.Scatterpolar(r=calidad_categoria[calidad_categoria["categoria"]=="Cultura"].iloc[:, :].values.tolist()[0][1:], 
    theta=calidad_categoria[calidad_categoria["categoria"]=="Cultura"].columns.tolist()[1:], 
    fill='toself',
    name="Cultura")
    )

radar_categoria.add_trace(
go.Scatterpolar(r=promedios, 
    theta=dimensiones, 
    fill='toself',
    name="Calidad Global")
)

radar_categoria.update_layout(
    polar=dict(radialaxis=dict(visible=True)),
    showlegend=True,
    margin=go.layout.Margin(l=50, r=50, t=20, b=1, pad=1),
    legend=go.layout.Legend(orientation="h", xanchor = "center", x = 0.5, y=-0.2)
)

opts_calidad = calidad_categoria.groupby("categoria").mean().index.tolist()
opts_calidad = [{"label": i, "value": i} for i in opts_calidad]

calidad_data.loc[:, "promedio"] = np.average(calidad_data.iloc[:, 4:], axis=1)

layout = html.Div(
        children=[
            dcc.Tabs(
                id="tabs-example", 
                value="descriptivo",
                className="contenedor_pestanas",
                    children=[
                        dcc.Tab(
                            label="Calidad de Datos", 
                            value="calidad",
                            className="pestanas"
                        ),
                        dcc.Tab(
                            label="Evolución Datos Abiertos", 
                            value="descriptivo",
                            className="pestanas"
                        )
                    ],
            ),
            html.Div(id='contenido-calidad'),
        ],
        className="body"
    )

def descriptivo():
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
                                    className="contenedor_textos_externos_izq",
                                    children=[
                                        html.H5(
                                            className="textos_aclaratorios_exp",
                                            children="""En las siguientes gráficas se podrá observar la información asociada a la evolución de los datos abiertos en Colombia, mostrando la cantidad de veces que ha sido actualizado un conjunto de datos y el número de veces que ha sido creado un nuevo para cada fecha evaluada. También se muestra los mismos elementos por categoría."""
                                        )
                                    ]
                                )
                            ]
                        ),
                        html.Div(
                            className="contenedor_graficas_derecha",
                            children=[
                                html.Img(
                                    className="mapa",
                                    src='data:image/png;base64,{}'.format(image_seguimiento_image.decode()))
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
                                html.H4(children="Tendencia de creación y actualización",
                                    className="titulos"
                                )
                            ]
                        ),
                        html.Div(
                            className="contenedor_textos_aclaratorios",
                            children=[
                                dcc.Markdown("""Esta gráfica muestra el comportamiento a través del tiempo de la creación de nuevos conjuntos de datos(barras azules)  y de la actualización de los ya existentes (barras rojas) en el portal datos.gov.co. La fecha de actualización aparece en el eje horizontal de la gráfica. Fuente: [Inventario de Datos](https://www.datos.gov.co/dataset/Asset-Inventory/sxce-zrhe)""",
                                    className="textos_aclaratorios"
                                ),
                                dcc.Markdown("""Instrucciones:  en esta gráfica puede seleccionar la categoría de “Conjuntos de Datos Nuevos” o la “Actualización de Conjuntos de Datos Existentes” dando clic encima de las barras azules o rojas. Si desea hacer “Zoom” en una parte en específico del gráfico, seleccione el área que desea visualizar. """,
                                    className="instrucciones"
                                )
                            ]
                        ),
                        html.Div(
                            className="contenedor_graficas",
                            children=[
                                dcc.Graph(
                                    id="nuevos-actualizados",
                                    figure=go.Figure(data=[nuevos, actualizados],
                                    layout=go.Layout(xaxis_title="Fecha de ejecución",
                                    yaxis_title="Cantidad de conjunto de datos nuevos - actualizados",
                                    margin=go.layout.Margin(l=50, r=50, t=5, b=5, pad=4),
                                    barmode="group",
                                    legend=go.layout.Legend(orientation="h")))
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
                                html.H4("Datos desagregados por fecha",
                                    className="titulos"
                                )
                            ]
                        ),
                        html.Div(
                            className="",
                            children=[
                                html.Div(
                                    className="contenedor_graficas_izquierda",
                                    children=[
                                        html.Div(
                                            className="contenedor_textos_externos",
                                            children=[
                                                dcc.Markdown("""En esta tabla se pueden realizar filtros por categoría de datos para obtener la cantidad de conjuntos de datos creados. Fuente: [Inventario de Datos](https://www.datos.gov.co/dataset/Asset-Inventory/sxce-zrhe).""",
                                                    className="textos_aclaratorios"
                                                )
                                            ]
                                        )  
                                    ]
                                ),
                                html.Div(
                                    className="contenedor_graficas_derecha",
                                    children=[
                                        html.Div(
                                            className="contendor-tablas_exp",
                                            children=[
                                                dash_table.DataTable(
                                                    id="tabla_categoria",
                                                    columns=[{'id': 'categoria', 'name': 'Categoria', 'type': 'text'},
                                                            {'id': 'fecha_ejecucion', 'name': 'Fecha Ejecución', 'type': 'datetime'},
                                                            {'id': 'actualizados', 'name': 'Actualizados', 'type': 'numeric'},
                                                            {'id': 'nuevos', 'name': 'Nuevos', 'type': 'numeric'}],
                                                    data=data_categoria.to_dict("records"),
                                                    style_cell_conditional=[{'if': {"column_id": "categoria"}, "width": "40%"},
                                                                            {'if': {'column_id': 'fecha_ejecucion'}, 'width': "20%"},
                                                                            {'if': {'column_id': 'actualizados'}, 'width': "15%", "textAlign": "center"},
                                                                            {'if': {'column_id': 'nuevos'}, 'width': "15%", "textAlign": "center"}],                                    
                                                    fixed_rows={'headers': True, 'data': 0},
                                                    filter_action="native",
                                                    sort_action="native",
                                                    sort_mode='multi',
                                                    style_cell={"font-family": "Work Sans", "fontSize": 13, "textAlign": "left", "color": "#004884"},
                                                    style_data={'height': 'auto', 'whiteSpace': 'normal'},
                                                    style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F2F2F2'}],
                                                    style_header={'backgroundColor': "#3366CC", 'fontWeight': 'bold', "color": "white"},
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
                ),
                html.Div(
                    className="contenedor_externo",
                    children=[
                        html.Div(
                            className="contenedor_titulos",
                            children=[
                                html.H4(children="Tendencia de creación y actualización",
                                    className="titulos"
                                )
                            ]
                        ),
                        html.Div(
                            className="contenedor_textos_aclaratorios",
                            children=[
                                dcc.Markdown("""Esta es una gráfica interactiva, en la cual se pueden seleccionar las categorías de los datos sobre las cuales se quiere observar la tendencia  de actualización de los conjuntos de datos y el cargue de los nuevos.  La fecha de actualización aparece en el eje horizontal de la gráfica. Fuente: [Inventario de Datos](https://www.datos.gov.co/dataset/Asset-Inventory/sxce-zrhe).""",
                                    className="textos_aclaratorios"
                                ),
                                html.H5("""Instrucciones:  en esta gráfica puede seleccionar la tendencia de actualización de datos por categoría, para hacerlo vaya al menú desplegable y escoja la categoría de su preferencia. Si dese hacer “Zoom” en una parte en específico del gráfico, seleccione el área que desea visualizar, para volver a la gráfica original, haga clic encima del icono “Casa” ubicado en la parte superior derecha del gráfico. """,
                                    className="instrucciones"
                                )
                            ]
                        ),
                        html.Div(
                            className="contenedor_selectores",
                            children=[
                                html.Div(
                                    className="contenedor_label_derecha",
                                    children=[
                                        html.Label("Categorias", className="selector_tiempo"),
                                    ]
                                ),
                                html.Div(
                                    className="contenedor_label_izquierda",
                                    children=[
                                        html.Label("Periodo de Tiempo", className="selector_tiempo")
                                    ]
                                )

                            ]
                        ),
                        html.Div(
                            className="contenedor_selectores",
                            children=[
                                html.Div(
                                    className="contenedor_label_derecha",
                                    children=[
                                        dcc.Dropdown(
                                            id="opt",
                                            options=opts,
                                            value=opts[1]["value"],
                                            className="selector_tiempo"
                                        )
                                    ]
                                ),
                                html.Div(
                                    className="contenedor_label_izquierda",
                                    children=[
                                        dcc.DatePickerRange(
                                            className="selector_tiempo",
                                            id="date-picker-range", 
                                            min_date_allowed=pd.to_datetime(min(data_categoria.fecha_ejecucion), format="%Y-%m-%d"),
                                            max_date_allowed=pd.to_datetime(max(data_categoria.fecha_ejecucion), format="%Y-%m-%d"),
                                            initial_visible_month=pd.to_datetime(min(data_categoria.fecha_ejecucion), format="%Y-%m-%d"),
                                            start_date=pd.to_datetime(min(data_categoria.fecha_ejecucion), format="%Y-%m-%d"),
                                            end_date=pd.to_datetime(max(data_categoria.fecha_ejecucion), format="%Y-%m-%d")
                                        )
                                    ]
                                )

                            ]
                        ),
                        html.Div(
                            className="contenedor_graficas",
                            children=[
                                dcc.Graph(
                                    id="example-graph-3", figure=fig)
                            ]
                        )
                    ]
                )
        ]
    )

def calidad():
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
                                    className="contenedor_textos_externos_derecha",
                                    children=[
                                        dcc.Markdown(
                                            children='''En esta sección los ciudadanos podrán observar de manera gráfica el resultado del análisis de calidad realizado a los conjuntos de datos publicados en el portal datos.gov.co. Esta medición se llevó a cabo con base en los criterios definidos en la Guía de Estándares de Calidad e Interoperabilidad de los Datos Abiertos de Colombia aplicados de manera consolidada sobre el total de conjuntos de datos, también se puede ver por categorías y de manera individual.''',
                                            className="textos_aclaratorios_exp"
                                        )
                                    ]
                                )
                            ]
                        ),
                        html.Div(
                            className="contenedor_graficas_izquierda_exp",
                            children=[
                                html.Img(
                                    className="mapa",
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
                                html.H4(children="Calidad global de todos los conjuntos de datos",
                                    className="titulos"
                                )
                            ]
                        ),
                        html.Div(
                            children=[
                                html.Div(
                                    className="contenedor_tex_izquierda_exp",
                                    children=[
                                        html.Div(
                                            className="contenedor_textos_externos",
                                            children=[
                                                html.H5("""En esta gráfica se muestra la medición de cada uno de los criterios de calidad sobre la totalidad de los conjuntos de datos disponibles en el portal datos.gov.co, mostrando como resultado la calidad promedio de todos los conjuntos de datos, en 10 categorías: Actualidad, Completitud, Comprensibilidad, Conformidad, Consistencia, Credibilidad, Disponibilidad, Exactitud, Portabilidad y Trazabilidad.""",
                                                    className="textos_aclaratorios"
                                                )
                                            ]
                                        )
                                    ]
                                ),
                                html.Div(
                                    className="contenedor_graficas_derecha",
                                    children=[
                                        dcc.Graph(
                                            id="example-graph-2-calidad",
                                            figure=radar_promedio
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
                                html.H4(children="Calidad por categoría",
                                    className="titulos"
                                )
                            ]
                        ),
                        html.Div(
                            className="contenedor_tex_derecha_exp",
                            children=[
                                html.Div(
                                    className="contenedor_textos_externos",
                                    children=[
                                        html.H5("""En esta gráfica interactiva se pueden observar las categorías en las cuales se encuentran clasificados los conjuntos de datos en el portal de datos abiertos, de tal manera que al seleccionar cada una de ellas se pueda obtener la medición de los criterios de calidad. Para poder comparar se muestra de fondo la gráfica del promedio general y delante la gráfica asociada a la calidad por categoría. El detalle de la evaluación de cada conjunto de datos se encuentra en la tabla de abajo.""",
                                            className="textos_aclaratorios"
                                        ),
                                        html.H5("""Instrucciones:  para poder ver el resultado en específico , seleccione la categoría y vea como esta se muestra comparándola con los resultados generales de todos los conjuntos de datos.""",
                                            className="instrucciones"
                                        )
                                    ]
                                )
                            ]
                        ),
                        html.Div(
                            className="contenedor_graficas_izquierda_exp",
                            children=[
                                html.Div(
                                    className="contenedor_selectores",
                                    children=[
                                        html.P(
                                            className="selector_tiempo",
                                            children=[
                                                html.Label("Categorias"),
                                                dcc.Dropdown(id="opt_calidad",
                                                    options=opts_calidad,
                                                    value=opts_calidad[1]["value"]
                                                )
                                            ]
                                        )
                                    ]
                                ),
                                html.Div(
                                    className="contenedor_graficas",
                                    children=[
                                        dcc.Graph(
                                            className="selector_tiempo",
                                            id="example-graph-3-calidad", figure=radar_categoria)
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
                                html.H4("Calidad por conjunto de datos",
                                    className="titulos"
                                )
                            ]
                        ),
                        html.Div(
                            className="contenedor_textos_aclaratorios",
                            children=[
                                html.H5("""Se muestra la medición de cada uno de los criterios de calidad definidos en la Guía de Estándares de Calidad e 
                                    Interoperabilidad de los Datos Abiertos del Gobierno de Colombia para cada uno de los conjuntos de datos disponibles.
                                    Fuentes: Conjuntos de datos disponibles en el portal datos.gov.co. Solo se toma al información clasificada como conjuntos de datos.""",
                                    className="textos_aclaratorios"
                                ),
                                html.H5("""Instrucciones: para ver el listado completo de la calificación de calidad puede desplazarse a la derecha usando la barra inferior o cambiar la página
                                    utilizando las flechas de la parte inferior izquierda de la tabla.""",
                                    className="textos_aclaratorios"
                                )
                            ]
                        ),
                        html.Div(
                            className="contenedor_tablas",
                            children=[
                                dash_table.DataTable(
                                    id="tabla_calidad_categoria",
                                    columns=[{'id': 'entidad', 'name': 'Entidad', 'type': 'text'},
                                            {'id': 'categoria', 'name': 'Categoria', 'type': 'text'},
                                            {'id': 'nombre', 'name': 'Conjunto de Datos', 'type': 'text'},
                                            {'id': 'Completitud', 'name': 'Completitud', 'type': 'numeric'},
                                            {'id': 'Credibilidad', 'name': 'Credibilidad', 'type': 'numeric'},
                                            {'id': 'Actualidad', 'name': 'Actualidad', 'type': 'numeric'},
                                            {'id': 'Trazabilidad', 'name': 'Trazabilidad', 'type': 'numeric'},
                                            {'id': 'Disponibilidad', 'name': 'Disponibilidad', 'type': 'numeric'},
                                            {'id': 'Conformidad', 'name': 'Conformidad', 'type': 'numeric'},
                                            {'id': 'Comprensibilidad', 'name': 'Comprensibilidad', 'type': 'numeric'},
                                            {'id': 'Portabilidad', 'name': 'Portabilidad', 'type': 'numeric'},
                                            {'id': 'Consistencia', 'name': 'Consistencia', 'type': 'numeric'},
                                            {'id': 'Exactitud', 'name': 'Exactitud', 'type': 'numeric'}],
                                    data=calidad_data.to_dict("records"),
                                    style_cell_conditional=[{'if': {"column_id": "entidad"}, "width": "10%"},
                                                            {'if': {'column_id': 'categoria'}, 'width': "10%"},
                                                            {'if': {'column_id': 'nombre'}, 'width': "10%"},
                                                            {'if': {'column_id': 'Completitud'}, 'width': "5%", "textAlign": "center"},
                                                            {'if': {'column_id': 'Credibilidad'}, 'width': "5%", "textAlign": "center"},
                                                            {'if': {'column_id': 'Actualidad'}, 'width': "5%", "textAlign": "center"},
                                                            {'if': {'column_id': 'Trazabilidad'}, 'width': "5%", "textAlign": "center"},
                                                            {'if': {'column_id': 'Disponibilidad'}, 'width': "5%", "textAlign": "center"},
                                                            {'if': {'column_id': 'Conformidad'}, 'width': "5%", "textAlign": "center"},
                                                            {'if': {'column_id': 'Comprensibilidad'}, 'width': "5%", "textAlign": "center"},
                                                            {'if': {'column_id': 'Portabilidad'}, 'width': "5%", "textAlign": "center"},
                                                            {'if': {'column_id': 'Consistencia'}, 'width': "5%", "textAlign": "center"},
                                                            {'if': {'column_id': 'Exactitud'}, 'width': "5%", "textAlign": "center"}],
                                    fixed_rows={'headers': True, 'data': 0},
                                    filter_action="native",
                                    sort_action="native",
                                    sort_mode='multi',
                                    style_cell={"font-family": "Work Sans", "fontSize": 13, "textAlign": "left", "color": "#004884"},
                                    style_data={'height': 'auto', 'whiteSpace': 'normal'},
                                    style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F2F2F2'}],
                                    style_table={"height": "400px"},
                                    style_header={'backgroundColor': "#3366CC", 'fontWeight': 'bold', "color": "white"},
                                    style_as_list_view=True,
                                    css=[{'selector': '.first-page, .current-page, .last-page, .page-number, .next-page, .previous-page, .page-number', 'rule': 'color: #004884'}]
                                )
                            ]
                        )
                    ]
                )
        ]
    )

image_filename = "/var/www/modelodatosabiertos/src/img/calidad.png"
# image_filename = "src/img/calidad.png"
encoded_image = base64.b64encode(open(image_filename, 'rb').read())

image_filename = "/var/www/modelodatosabiertos/src/img/seguimiento.png"
# image_filename = "src/img/seguimiento.png"
image_seguimiento_image = base64.b64encode(open(image_filename, 'rb').read())

@app.callback(dash.dependencies.Output('contenido-calidad', 'children'),
              [dash.dependencies.Input('tabs-example', 'value')])
def render_content(tab):
    if tab == "descriptivo":
        return descriptivo()

    elif tab == "calidad":
        return calidad()

@app.callback(dash.dependencies.Output(component_id="example-graph-3", component_property="figure"),
              [dash.dependencies.Input(component_id="opt", component_property="value"),
               dash.dependencies.Input(component_id="date-picker-range", component_property="start_date"),
               dash.dependencies.Input(component_id="date-picker-range", component_property="end_date")])
def update_figure(input1, start_date, end_date):
    if start_date and end_date is not None:

        aux = data_categoria.iloc[[pd.to_datetime(item) >= pd.to_datetime(start_date) and pd.to_datetime(
            item) <= pd.to_datetime(end_date) for item in data_categoria.fecha_ejecucion]]
        aux = aux.loc[aux.categoria == input1, :]
        nuevos_categoria = go.Scatter(
            x=aux.fecha_ejecucion,  y=aux.nuevos, name="Nuevos")
        actualizados_categoria = go.Scatter(
            x=aux.fecha_ejecucion, y=aux.actualizados, name="Actualizados")

        fig_layout = go.Layout(xaxis_title="Fecha de ejecución",
                               yaxis_title="Cantidad de conjunto de datos nuevos - actualizados",
                               margin=go.layout.Margin(
                                   l=10, r=10, t=10, b=10, pad=4),
                               barmode="stack",
                               legend=go.layout.Legend(orientation="h"))

        fig = go.Figure(
            data=[nuevos_categoria, actualizados_categoria], layout=fig_layout)
        return fig

@app.callback(dash.dependencies.Output(component_id="example-graph-3-calidad", component_property="figure"),
              [dash.dependencies.Input(component_id="opt_calidad", component_property="value")])
def update_figure(input1):

    aux = calidad_categoria[calidad_categoria["categoria"]==input1].iloc[:, :].values.tolist()[0][1:]
    columns = calidad_categoria[calidad_categoria["categoria"]==input1].columns.tolist()[1:]

    radar_categoria = go.Figure()
    
    radar_categoria.add_trace(
        go.Scatterpolar(r=aux, 
        theta=columns, 
        fill='toself',
        name="{}".format(input1))
    )

    radar_categoria.add_trace(
        go.Scatterpolar(r=promedios, theta=dimensiones, fill='toself', 
        name="Calidad Global")
    )

    radar_categoria.update_layout(
        polar=dict(radialaxis=dict(visible=True)),
        showlegend=True,
        margin=go.layout.Margin(l=50, r=50, t=20, b=1, pad=1),
        legend=go.layout.Legend(orientation="h", xanchor = "center", x = 0.5, y=-0.2))
    return radar_categoria


if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port="8050")
