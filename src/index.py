import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from flask import Flask

from app import app
import calidad as calidad_app
import territorial as territorial_app

server = app.server

external_stylesheets = ["https://fonts.googleapis.com/css?family=Montserrat&display=swap", "https://fonts.googleapis.com/css?family=Work+Sans&display=swap"]

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

@app.callback(Output('page-content', 'children'),
              [Input('url', 'pathname')])
def display_page(pathname):
    if pathname == '/calidad/':
        return calidad_app.layout
    elif pathname == '/territorial/':
        return territorial_app.layout
    else:
        return '404'

if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port="8050")