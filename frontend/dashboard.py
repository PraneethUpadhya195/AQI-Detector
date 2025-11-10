import dash
from dash import dcc, html, Input, Output, State, callback, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import requests
import pandas as pd
from datetime import datetime

# --- Configuration ---
API_BASE_URL = "http://127.0.0.1:5000"

# --- App Initialization ---
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG])

# --- Helper Function ---
def get_aqi_color_class(category):
    """Returns a Bootstrap text color class based on the AQI category."""
    mapping = {
        "Good": "text-success",
        "Satisfactory": "text-success", # Lighter green, but success works
        "Moderate": "text-warning",
        "Poor": "text-danger",
        "Very Poor": "text-danger", # Stronger red
        "Severe": "text-danger",  # Even stronger red
    }
    return mapping.get(category, "text-white")

# --- App Layout ---
app.layout = dbc.Container(fluid=True, children=[
    # dcc.Store holds data in memory for sharing between callbacks
    # This will hold our main data for the chart and CSV download
    dcc.Store(id='history-data-store'),

    # This component is for triggering the CSV download
    dcc.Download(id="download-csv"),

    # Main Title
    dbc.Row([
        dbc.Col(html.H1("Manual AQI Calculator & Data Logger", className="text-center text-white my-4"))
    ]),
    
    dbc.Row([
        # --- Column 1: Manual Calculator ---
        dbc.Col(md=4, children=[
            dbc.Card([
                dbc.CardHeader(html.H4("Enter Pollutant Values")),
                dbc.CardBody([
                    dbc.Input(id='manual-source', placeholder='Source Name (e.g., "Home Sensor")', type='text', className="mb-2"),
                    html.Hr(),
                    # Create inputs for all 8 pollutants
                    dbc.Input(id='manual-pm25', placeholder='PM2.5 (µg/m³)', type='number', className="mb-2"),
                    dbc.Input(id='manual-pm10', placeholder='PM10 (µg/m³)', type='number', className="mb-2"),
                    dbc.Input(id='manual-co', placeholder='CO (mg/m³)', type='number', className="mb-2"),
                    dbc.Input(id='manual-no2', placeholder='NO2 (µg/m³)', type='number', className="mb-2"),
                    dbc.Input(id='manual-so2', placeholder='SO2 (µg/m³)', type='number', className="mb-2"),
                    dbc.Input(id='manual-o3', placeholder='O3 (µg/m³)', type='number', className="mb-2"),
                    dbc.Input(id='manual-nh3', placeholder='NH3 (µg/m³)', type='number', className="mb-2"),
                    dbc.Input(id='manual-pb', placeholder='Lead (Pb) (µg/m³)', type='number', className="mb-2"),
                    
                    dbc.Button("Calculate & Save", id='calculate-button', color='primary', className="w-100 mt-3"),
                ])
            ], color="dark", outline=True),
            
            dbc.Card([
                dbc.CardHeader(html.H4("Calculation Result")),
                # This Div is where the "AQI: 266 (Poor)" message will appear
                dbc.CardBody(id='calc-output-div', children=[
                    html.P("Enter values and click 'Calculate' to see the result.")
                ])
            ], color="dark", outline=True, className="mt-4")
        ]),
        
        # --- Column 2: History & Chart ---
        dbc.Col(md=8, children=[
            dbc.Card([
                dbc.CardHeader(html.H4("Data History")),
                dbc.CardBody([
                    dbc.Button("Download as CSV", id="btn-download-csv", color="secondary", className="mb-3"),
                    # This Div will hold the data table
                    html.Div(id='history-table-div')
                ])
            ], color="dark", outline=True),

            dbc.Card([
                dbc.CardHeader(html.H4("Pollutant Chart")),
                dbc.CardBody([
                    # The chart will automatically have zoom, pan, and PNG download options
                    dcc.Graph(id='pollutant-chart')
                ])
            ], color="dark", outline=True, className="mt-4")
        ])
    ])
])

# --- Callbacks ---

@callback(
    # This callback updates TWO things: the result text AND the history data store
    Output('calc-output-div', 'children'),
    Output('history-data-store', 'data'), # This triggers the table/chart refresh
    Input('calculate-button', 'n_clicks'),
    [State('manual-source', 'value'),
     State('manual-pm25', 'value'),
     State('manual-pm10', 'value'),
     State('manual-co', 'value'),
     State('manual-no2', 'value'),
     State('manual-so2', 'value'),
     State('manual-o3', 'value'),
     State('manual-nh3', 'value'),
     State('manual-pb', 'value')],
    prevent_initial_call=True
)
def handle_manual_calculation(n_clicks, source, pm25, pm10, co, no2, so2, o3, nh3, pb):
    """
    Callback for the manual calculation button.
    Sends data to the Flask API and displays the result.
    """
    try:
        payload = {
            "source": source,
            "pm25": float(pm25) if pm25 else None,
            "pm10": float(pm10) if pm10 else None,
            "co": float(co) if co else None,
            "no2": float(no2) if no2 else None,
            "so2": float(so2) if so2 else None,
            "o3": float(o3) if o3 else None,
            "nh3": float(nh3) if nh3 else None,
            "pb": float(pb) if pb else None
        }
        
        response = requests.post(f"{API_BASE_URL}/api/calculate_manual", json=payload)
        
        if response.status_code == 200:
            result = response.json()
            
            # 1. Create the colored result message
            color_class = get_aqi_color_class(result['category'])
            result_message = html.Div([
                html.H3(f"AQI: {result['aqi']}", className=f"font-weight-bold {color_class}"),
                html.P(f"Category: {result['category']}", className=color_class),
                html.P(f"Dominant Pollutant: {result['dominant_pollutant']}")
            ])
            
            # 2. Return the message and also update the data store
            # Updating the store with new data will trigger the next callback
            return result_message, result 
        else:
            return dbc.Alert(f"API Error: {response.text}", color="danger"), dash.no_update
            
    except Exception as e:
        return dbc.Alert(f"An error occurred: {e}", color="danger"), dash.no_update

@callback(
    # This callback updates the table and the chart
    Output('history-table-div', 'children'),
    Output('pollutant-chart', 'figure'),
    # It's triggered when the app loads OR when the history-data-store is updated
    [Input('history-data-store', 'data')] 
)
def update_history(new_data):
    """
    Fetches all data from the API and updates the history table and chart.
    """
    try:
        # Fetch all data from our new API endpoint
        api_url = f"{API_BASE_URL}/api/get_all_data"
        response = requests.get(api_url)
        data = response.json()
        
        if not data:
            # No data found
            return html.P("No history data found."), go.Figure()

        # Convert the JSON data to a pandas DataFrame
        df = pd.DataFrame(data)
        
        # --- 1. Create the History Table ---
        # We only want to show a few key columns
        table_df = df[['timestamp', 'source', 'aqi', 'category', 'dominant_pollutant']]
        # Format the timestamp to be readable
        table_df['timestamp'] = pd.to_datetime(table_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        history_table = dbc.Table.from_dataframe(
            table_df, 
            striped=True, 
            bordered=True, 
            hover=True,
            responsive=True,
            # dark=True # <-- THIS LINE CAUSED THE ERROR AND IS NOW REMOVED
        )
        
        # --- 2. Create the Pollutant Chart ---
        # The chart has zoom/pan/download-as-PNG built-in!
        fig = go.Figure()
        
        # We need to reverse the dataframe so the chart shows oldest-to-newest
        df_chart = df.iloc[::-1] 
        
        # Add traces for the main pollutants
        fig.add_trace(go.Trace(x=df_chart['timestamp'], y=df_chart['pm25_raw'], name='PM2.5', mode='lines+markers'))
        fig.add_trace(go.Trace(x=df_chart['timestamp'], y=df_chart['pm10_raw'], name='PM10', mode='lines+markers'))
        fig.add_trace(go.Trace(x=df_chart['timestamp'], y=df_chart['co_raw'], name='CO', mode='lines+markers'))
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font={'color': 'white'},
            legend_title_text='Pollutants'
        )

        return history_table, fig

    except Exception as e:
        return dbc.Alert(f"Error loading history: {e}", color="danger"), go.Figure()


@callback(
    Output("download-csv", "data"),
    Input("btn-download-csv", "n_clicks"),
    State("history-data-store", "data"), # Get data from the store
    prevent_initial_call=True,
)
def download_csv(n_clicks, data):
    """
    When the download button is clicked,
    fetch all data and convert it to a CSV string for download.
    """
    # We don't even need the 'data' from the store, we can just fetch fresh
    api_url = f"{API_BASE_URL}/api/get_all_data?limit=9999" # Get all data
    response = requests.get(api_url)
    all_data = response.json()
    df = pd.DataFrame(all_data)
    
    # Convert dataframe to CSV string and send it to the dcc.Download component
    return dcc.send_data_frame(df.to_csv, "aqi_history.csv", index=False)


# --- Main execution ---
if __name__ == '__main__':
    app.run(debug=True, port=8050)