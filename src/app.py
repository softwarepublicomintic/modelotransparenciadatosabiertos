from flask import Flask
import dash

external_stylesheets = ["https://fonts.googleapis.com/css?family=Montserrat&display=swap", "https://fonts.googleapis.com/css?family=Work+Sans&display=swap"]

server = Flask(__name__)
app = dash.Dash(__name__, server=server, external_stylesheets=external_stylesheets)
app.config['suppress_callback_exceptions'] = True
app.title = "Calidad"