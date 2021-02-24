#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.io as pio
import plotly.figure_factory as ff
import plotly.graph_objects as go
import pandas as pd
import configparser

from plotly.subplots import make_subplots
from dash.dependencies import Input, Output
from EnvironmentSensor import EnvironmentSensor
from KostalPlenticore import SolarPoller

config = configparser.ConfigParser()
config.read('config.conf')
poll_time = float(config.get('PiEnvironmentSensor', 'sensor_poll_time'))
debug_flag = config.getboolean('DEFAULT', 'debug')
dashboard_name = config.get('DEFAULT', 'dashboard_name')
ip_address_converter = config.get('Converter', 'device_ip')
password_converter = config.get('Converter', 'password')
converter_poll_time = float(config.get('Converter', 'converter_poll_time'))


def setup_app():
    environment_sensor = EnvironmentSensor(
        poll_time=poll_time,
        debug=debug_flag
    )
    solar_poller = SolarPoller(
        ip=ip_address_converter,
        password=password_converter,
        poll_time=converter_poll_time,
        debug=debug_flag
    )
    environment_sensor.start()
    solar_poller.start()


def draw_solar_figure():
    df = pd.read_csv('temp.csv', header=5)
    df.Zeit = pd.DatetimeIndex(
        pd.to_datetime(df.Zeit, unit='s')).tz_localize('Etc/UTC').tz_convert('Europe/Zurich').tz_localize(None)
    sub_df = df[['Zeit', 'HC1 P', 'HC2 P', 'HC3 P', 'SOC H', 'DC1 P', 'DC2 P']]
    sub_df = sub_df.fillna(method='pad')
    sub_df['DC P'] = sub_df['DC1 P'] + sub_df['DC2 P']
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(
            x=sub_df['Zeit'],
            y=sub_df['SOC H'],
            name='Battery Charge Status',
            mode='lines',
            fill='tozeroy',
            opacity=0.1,
            hoverinfo='name+y'
        ),
        secondary_y=True,
    )
    fig.add_trace(
        go.Scatter(
            x=sub_df['Zeit'],
            y=sub_df['DC P'],
            name='Energy Production',
            mode='lines',
            fill='tozeroy',
            hoverinfo='name+y'
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=sub_df['Zeit'],
            y=sub_df['HC1 P'],
            name='Battery Consumption',
            mode='lines',
            hoverinfo='name+y'
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=sub_df['Zeit'],
            y=sub_df['HC2 P'],
            name='PV Consumption',
            mode='lines',
            hoverinfo='name+y'
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=sub_df['Zeit'],
            y=sub_df['HC3 P'],
            name='Grid Consumption',
            mode='lines',
            hoverinfo='name+y'
        ),
        secondary_y=False,
    )
    fig.update_xaxes(title_text="Datum und Zeit", dtick=7200000.0)
    fig.update_yaxes(title_text="Power Consumption [W]", secondary_y=False)
    fig.update_yaxes(title_text="Battery Charge [%]", secondary_y=True, range=[-5, 110])
    fig.layout.template = 'simple_white'
    return fig


def get_environment_stats():
    env_df = pd.read_csv('environment.log')
    latest = env_df.tail(1)
    return latest.Temperature.values[0], latest.Pressure.values[0], latest.Humidity.values[0]


setup_app()
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server
pio.templates.default = "ggplot2"

# Default Graphs
env_table = ff.create_table(
    [
        ['Temperatur', 'Luftdruck', 'Feuchtigkeit'],
        ['25.0°C', '1025.2mbar', '48.3% Rel. Luftf.']
    ]
)
for i in range(len(env_table.layout.annotations)):
    env_table.layout.annotations[i].font.size = 20

app.layout = html.Div(
    children=[
        html.H1(dashboard_name),
        dcc.Tabs(
            children=[
                dcc.Tab(
                    label='Umgebungsmonitor',
                    children=[dcc.Graph(id='environment-stats', figure=env_table),
                              dcc.Interval(
                                  id='environment-interval',
                                  interval=10 * 1000,
                                  n_intervals=0
                              )]
                ),
                dcc.Tab(
                    label='Solaranlage',
                    children=[
                        dcc.Graph(id='solar-lastday', figure=draw_solar_figure()),
                        dcc.Interval(
                            id='solar-interval',
                            interval=30 * 1000,
                            n_intervals=0
                        )]
                )
            ],
            mobile_breakpoint=0
        )
    ]
)


@app.callback(Output('environment-stats', 'figure'),
              [Input('environment-interval', 'n_intervals')])
def update_environment_status():
    temperature, pressure, humidity = get_environment_stats()
    env_table = ff.create_table(
        [
            ['Temperatur', 'Luftdruck', 'Feuchtigkeit'],
            [
                '{0:4.2f}°C'.format(temperature),
                '{0:5.2f} mbar'.format(pressure),
                '{0:3.2f}% Relative Luftfeuchtigkeit'.format(humidity)
            ]
        ]
    )
    for index in range(len(env_table.layout.annotations)):
        env_table.layout.annotations[index].font.size = 25
    return env_table


@app.callback(Output('solar-lastday', 'figure'),
              [Input('solar-interval', 'n_intervals')])
def update_solar_figure():
    return draw_solar_figure()
