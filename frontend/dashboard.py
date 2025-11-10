import dash
from dash import dcc, html, Input, Output, State, callback, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import requests
import pandas as pd
from datetime import datetime
# This new import is for the download icon
from dash_iconify import DashIconify

# --- Configuration ---
API_BASE_URL = "http://127.0.0.1:5000"
POLLUTANT_LIST = ['pm25', 'pm10', 'co', 'no2', 'so2', 'o3', 'nh3']

# --- App Initialization ---
# We use a basic theme and override it with our own CSS
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# --- Helper Functions ---
def get_aqi_color_class(category):
    """Returns a Bootstrap text color class based on the AQI category."""
    mapping = {
        "Good": "text-success",
        "Satisfactory": "text-success-light", # A custom class we'll define
        "Moderate": "text-warning",
        "Poor": "text-danger-light", # A custom class we'll define
        "Very Poor": "text-danger",
        "Severe": "text-danger-severe", # A custom class we'll define
    }
    return mapping.get(category, "text-white")

def build_pollutant_chart(df):
    """Builds the main pollutant chart with a dark theme."""
    fig = go.Figure()
    
    # We need to reverse the dataframe so the chart shows oldest-to-newest
    df_chart = df.iloc[::-1]

    # Map of internal keys to display names
    pollutant_display_names = {
        'pm25_raw': 'PM2.5',
        'pm10_raw': 'PM10',
        'co_raw': 'CO',
        'no2_raw': 'NO2',
        'so2_raw': 'SO2',
        'o3_raw': 'O3',
        'nh3_raw': 'NH3',
        'pb_raw': 'Lead (Pb)'
    }

    for key, display_name in pollutant_display_names.items():
        if key in df_chart.columns and df_chart[key].notna().any():
            fig.add_trace(go.Trace(
                x=df_chart['timestamp'], 
                y=df_chart[key], 
                name=display_name, 
                mode='lines+markers'
            ))

    fig.update_layout(
        paper_bgcolor='#000000',  # Black paper background
        plot_bgcolor='#000000',   # Black plot background
        font={'color': 'white'},
        legend_title_text='Pollutants',
        xaxis_title="Timestamp",
        yaxis_title="Concentration"
    )
    return fig

# --- App Layout ---
app.layout = html.Div(style={
    'background': 'linear-gradient(to bottom, #0a2e38, #000000)', # Dark green-blue to black
    'minHeight': '100vh',
    'color': 'white'
}, children=[
    dcc.Store(id='history-data-store'),
    dcc.Download(id="download-csv"),
    
    # --- FIX 2: Added dummy components for the CSS callback ---
    html.Div(id='dummy-input-for-css', style={'display': 'none'}),
    html.Div(id='dummy-output-for-css', style={'display': 'none'}),
    # --- End of fix ---

    dbc.Container(fluid=True, children=[
        # Main Title
        dbc.Row([
            dbc.Col(html.H1("Manual AQI Calculator & Data Logger", className="text-center my-4"))
        ]),
        
        # --- Row 1: Chart and Table (Your new layout) ---
        dbc.Row([
            # Column 1: Pollutant Chart
            dbc.Col(md=7, children=[
                dbc.Card(className="shadow", children=[
                    dbc.CardHeader(html.H4("Pollutant History")),
                    dbc.CardBody([
                        dcc.Graph(
                            id='pollutant-chart',
                            config={'scrollZoom': True, 'displaylogo': False}
                        )
                    ])
                ], style={'backgroundColor': '#1a1a1a', 'border': '1px solid #222'})
            ]),
            
            # Column 2: Data History Table
            dbc.Col(md=5, children=[
                dbc.Card(className="shadow", children=[
                    dbc.CardHeader(html.H4(children=[
                        "Data History",
                        # Download icon button
                        dbc.Button(
                            DashIconify(icon="fa-solid:download", width=20),
                            id="btn-download-csv",
                            color="primary",
                            className="float-end",
                            size="sm"
                        )
                    ])),
                    dbc.CardBody([
                        html.Div(id='history-table-div', children=[
                            # This will be filled by the callback
                        ])
                    ])
                ], style={'backgroundColor': '#1a1a1a', 'border': '1px solid #222'})
            ]),
        ]),
        
        # --- Row 2: The Calculator (Your new layout) ---
        dbc.Row(className="mt-5 justify-content-center", children=[
            dbc.Col(md=10, children=[
                dbc.Card(className="shadow", children=[
                    dbc.CardHeader(html.H3("Calculate New AQI")),
                    dbc.CardBody([
                        # Input Row 1
                        dbc.Row([
                            dbc.Col(md=3, children=[
                                html.Label("Source Name"),
                                dbc.Input(id='manual-source', placeholder='e.g., "Home Sensor"', type='text', className="mb-2")
                            ]),
                            dbc.Col(md=3, children=[
                                html.Label("PM2.5 (µg/m³)"),
                                dbc.Input(id='manual-pm25', type='number', className="mb-2")
                            ]),
                            dbc.Col(md=3, children=[
                                html.Label("PM10 (µg/m³)"),
                                dbc.Input(id='manual-pm10', type='number', className="mb-2")
                            ]),
                            dbc.Col(md=3, children=[
                                html.Label("CO (mg/m³)"),
                                dbc.Input(id='manual-co', type='number', className="mb-2")
                            ]),
                        ]),
                        # Input Row 2
                        dbc.Row([
                            dbc.Col(md=3, children=[
                                html.Label("NO2 (µg/m³)"),
                                dbc.Input(id='manual-no2', type='number', className="mb-2")
                            ]),
                            dbc.Col(md=3, children=[
                                html.Label("SO2 (µg/m³)"),
                                dbc.Input(id='manual-so2', type='number', className="mb-2")
                            ]),
                            dbc.Col(md=3, children=[
                                html.Label("O3 (µg/m³)"),
                                dbc.Input(id='manual-o3', type='number', className="mb-2")
                            ]),
                            dbc.Col(md=3, children=[
                                html.Label("NH3 (µg/m³)"),
                                dbc.Input(id='manual-nh3', type='number', className="mb-2")
                            ]),
                        ]),
                        # Button and Result Row
                        dbc.Row(className="mt-3 align-items-center", children=[
                            dbc.Col(md=4, children=[
                                dbc.Button("Calculate & Save", id='calculate-button', color='primary', size="lg", className="w-100")
                            ]),
                            # This is where the result "AQI: 266 (Poor)" appears
                            dbc.Col(md=8, id='calc-output-div', className="text-center")
                        ])
                    ])
                ], style={'backgroundColor': '#1a1a1a', 'border': '1px solid #222'})
            ])
        ])
    ])
])

# --- Callbacks ---

@callback(
    Output('calc-output-div', 'children'),
    Output('history-data-store', 'data'), # This triggers the table/chart refresh
    Input('calculate-button', 'n_clicks'),
    [State('manual-source', 'value')] + [State(f'manual-{p}', 'value') for p in POLLUTANT_LIST],
    prevent_initial_call=True
)
def handle_manual_calculation(n_clicks, source, *pollutant_values):
    """
    Callback for the manual calculation button.
    Sends data to the Flask API and displays the result.
    """
    try:
        # Create the payload dictionary using the pollutant list
        payload = {"source": source}
        for i, pollutant in enumerate(POLLUTANT_LIST):
            value = pollutant_values[i]
            payload[pollutant] = float(value) if value else None
        
        response = requests.post(f"{API_BASE_URL}/api/calculate_manual", json=payload)
        
        if response.status_code == 200:
            result = response.json()
            
            color_class = get_aqi_color_class(result['category'])
            result_message = html.Div([
                html.H2(f"AQI: {result['aqi']}", className=f"font-weight-bold {color_class}"),
                html.H4(f"({result['category']})", className=f" {color_class}"),
                html.P(f"Dominant: {result['dominant_pollutant'].upper()}")
            ])
            
            return result_message, result 
        else:
            return dbc.Alert(f"API Error: {response.text}", color="danger"), dash.no_update
            
    except Exception as e:
        return dbc.Alert(f"An error occurred: {e}", color="danger"), dash.no_update

@callback(
    Output('history-table-div', 'children'),
    Output('pollutant-chart', 'figure'),
    [Input('history-data-store', 'data')], # Triggered by app load or new data
    prevent_initial_call=False # Run on app load
)
def update_history_and_chart(new_data):
    """
    Fetches all data from the API and updates the history table and chart.
    """
    try:
        api_url = f"{API_BASE_URL}/api/get_all_data"
        response = requests.get(api_url)
        data = response.json()
        
        if not data:
            return html.P("No history data found. Calculate an AQI to get started!"), go.Figure().update_layout(
                paper_bgcolor='#000000', plot_bgcolor='#000000', font={'color': 'white'}
            )

        df = pd.DataFrame(data)
        
        # --- 1. Create the History Table ---
        table_df = df[['timestamp', 'source', 'aqi', 'category', 'dominant_pollutant']]
        table_df['timestamp'] = pd.to_datetime(table_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        history_table = dash_table.DataTable(
            data=table_df.to_dict('records'),
            columns=[{'name': i.replace('_', ' ').title(), 'id': i} for i in table_df.columns],
            style_cell={'textAlign': 'left', 'backgroundColor': '#333', 'color': 'white'},
            style_header={'backgroundColor': '#111', 'fontWeight': 'bold'},
            style_table={'overflowY': 'auto', 'height': '400px'}, # Makes table scrollable
            page_size=10,
        )
        
        # --- 2. Create the Pollutant Chart ---
        chart_fig = build_pollutant_chart(df)

        return history_table, chart_fig

    except Exception as e:
        return dbc.Alert(f"Error loading history: {e}", color="danger"), go.Figure()

@callback(
    Output("download-csv", "data"),
    Input("btn-download-csv", "n_clicks"),
    prevent_initial_call=True,
)
def download_csv(n_clicks):
    """
    When the download button is clicked,
    fetch all data and convert it to a CSV string for download.
    """
    # --- THIS IS THE SYNTAX FIX ---
    api_url = f"{API_BASE_URL}/api/get_all_data?limit=9999" # Get all data
    # --- END OF FIX ---
    
    response = requests.get(api_url)
    all_data = response.json()
    df = pd.DataFrame(all_data)
    
    return dcc.send_data_frame(df.to_csv, "aqi_history.csv", index=False)


# --- Custom CSS for new theme ---
# This is a hacky way to add CSS in Dash without a separate .css file
app.clientside_callback(
    """
    function(n) {
        // Create the <style> tag
        var style = document.createElement('style');
        style.innerHTML = `
            body {
                /* Your custom gradient */
                background: linear-gradient(to bottom, #0a2e38, #000000) !important;
                background-attachment: fixed;
            }
            .card {
                /* Semi-transparent dark cards */
                background-color: rgba(26, 26, 26, 0.8) !important;
                border: 1px solid #222 !important;
                color: white !important;
            }
            .card-header {
                background-color: rgba(0, 0, 0, 0.3) !important;
                border-bottom: 1px solid #222 !important;
            }
            /* Style the data table */
            .dash-table-container .dash-header, 
            .dash-table-container .dash-data-row {
                background-color: #333 !important;
                color: white !video !important;
            }
            .dash-table-container .dash-header {
                background-color: #111 !important;
                font-weight: bold !important;
            }
            .dash-table-container .dash-cell {
                border-color: #555 !important;
            }
            
            /* Custom text colors for AQI */
            .text-success-light { color: #a0d64a !important; }
            .text-danger-light { color: #f28e2c !important; }
            .text-danger-severe { color: #760013 !important; }
        `;
        // Add it to the document's <head>
        document.head.appendChild(style);
        return ""; // Return value doesn't matter
    }
    """,
    Output('dummy-output-for-css', 'children'), # We need an output
    Input('dummy-input-for-css', 'children') # We need an input
)

# --- Main execution ---
if __name__ == '__main__':
    app.run(debug=True, port=8050)