import dash
from dash import dcc, html, Input, Output, State, callback, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import requests
import pandas as pd
from datetime import datetime
from dash_iconify import DashIconify
import numpy as np

# --- Configuration ---
API_BASE_URL = "http://127.0.0.1:5000"
POLLUTANT_LIST = ['pm25', 'pm10', 'co', 'no2', 'so2', 'o3', 'nh3']

# --- App Initialization ---
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# --- Helper Functions ---
def get_aqi_color_class(category):
    """
    Returns a standard, simple Bootstrap text color class.
    """
    mapping = {
        "Good": "text-success",
        "Satisfactory": "text-success",
        "Moderate": "text-warning",
        "Poor": "text-danger",
        "Very Poor": "text-danger",
        "Severe": "text-danger",
    }
    return mapping.get(category, "text-light") # Default to light text

def build_pollutant_chart(df):
    """Builds the main pollutant chart with the new dark theme."""
    fig = go.Figure()
    df_chart = df.iloc[::-1] # Reverse for plotting
    
    pollutant_display_names = {
        'pm25_raw': 'PM2.5', 'pm10_raw': 'PM10', 'co_raw': 'CO',
        'no2_raw': 'NO2', 'so2_raw': 'SO2', 'o3_raw': 'O3',
        'nh3_raw': 'NH3'
    }
    
    for key, display_name in pollutant_display_names.items():
        if key in df_chart.columns and df_chart[key].notna().any():
            fig.add_trace(go.Trace(
                x=df_chart['timestamp'], y=df_chart[key], 
                name=display_name, mode='lines+markers'
            ))

    # Use a dark template for the chart
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor='#000000',  # Pitch black background
        plot_bgcolor='#000000',   # Pitch black plot area
        font={'color': '#f0f0f0'},
        legend_title_text='Pollutants',
        xaxis_title="Timestamp (IST)", 
        yaxis_title="Concentration",
        xaxis=dict(gridcolor='#444444'), # Darker gridlines
        yaxis=dict(gridcolor='#444444')
    )
    return fig

def create_stat_card(title, value, id_name):
    """Creates a small card for the new statistics row."""
    return dbc.Col(
        dbc.Card(
            dbc.CardBody([
                html.H6(title, className="card-title text-white"),
                html.H3(value, id=id_name, className=f"card-text font-weight-bold")
            ]),
        ),
        md=3
    )

# --- App Layout ---
app.layout = html.Div(id='main-wrapper', children=[
    dcc.Store(id='history-data-store'),
    dcc.Download(id="download-csv"),
    html.Div(id='dummy-input-for-css', style={'display': 'none'}),
    html.Div(id='dummy-output-for-css', style={'display': 'none'}),

    dbc.Container(fluid=True, className="py-4", children=[
        # Main Title
        dbc.Row([
            dbc.Col(html.H1("AQI Calculator & Data Logger", className="text-center my-4"))
        ]),
        
        # --- Statistical Overview Row (TOP) ---
        # --- FIX: Added more margin-bottom ---
        dbc.Row(id='stats-row', className="mb-5 justify-content-center", children=[ # mb-4 to mb-5
            create_stat_card("Average AQI", "-", "avg-aqi-stat"),
            create_stat_card("Max AQI", "-", "max-aqi-stat"),
            create_stat_card("Std. Deviation", "-", "std-aqi-stat"),
            create_stat_card("Total Records", "-", "total-records-stat"),
        ]),

        # --- Collapsible Calculator (YOUR IDEA) ---
        # --- FIX: Added more margin-bottom ---
        dbc.Row(className="mb-5", children=[ # mb-3 to mb-5
            dbc.Col([
                dbc.Button(
                    children=[
                        DashIconify(icon="mdi:calculator", className="me-2"),
                        "Show/Hide Calculator"
                    ],
                    id="collapse-button",
                    className="mb-3",
                    color="primary",
                    outline=True
                ),
                dbc.Collapse(
                    dbc.Card(children=[
                        dbc.CardHeader(html.H3("Calculate New AQI")),
                        dbc.CardBody([
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
                            dbc.Row(className="mt-3 align-items-center", children=[
                                dbc.Col(md=4, children=[
                                    dbc.Button("Calculate & Save", id='calculate-button', color='primary', size="lg", className="w-100")
                                ]),
                                dbc.Col(md=8, id='calc-output-div', className="text-center")
                            ])
                        ])
                    ]),
                    id="collapse",
                    is_open=False, # Calculator is HIDDEN by default
                ),
            ])
        ]),
        
        # --- Main Data Area: Chart and Table ---
        
        # --- FIX: Added more margin-bottom ---
        dbc.Row(className="mb-5", children=[ # mb-4 to mb-5
            dbc.Col(md=12, children=[
                dbc.Card(children=[
                    dbc.CardHeader(html.H4("Pollutant History")),
                    dbc.CardBody(dcc.Graph(
                        id='pollutant-chart',
                        config={'scrollZoom': True, 'displaylogo': False}
                    ))
                ])
            ])
        ]),
        
        # --- FIX: Centered and narrowed table ---
        dbc.Row(className="justify-content-center", children=[ # Center the row
            dbc.Col(md=10, children=[ # Use 10 of 12 columns
                dbc.Card(children=[
                    dbc.CardHeader(html.H4(children=[
                        "Data History",
                        dbc.Button(
                            DashIconify(icon="fa-solid:download", width=20),
                            id="btn-download-csv", color="secondary",
                            className="float-end", size="sm", outline=True
                        )
                    ])),
                    dbc.CardBody(html.Div(id='history-table-div'))
                ])
            ])
        ])
    ])
])

# --- Callbacks ---

# Callback to toggle the calculator
@callback(
    Output("collapse", "is_open"),
    [Input("collapse-button", "n_clicks")],
    [State("collapse", "is_open")],
    prevent_initial_call=True,
)
def toggle_collapse(n, is_open):
    if n:
        return not is_open
    return is_open

# Callback for the calculator button
@callback(
    Output('calc-output-div', 'children'),
    Output('history-data-store', 'data'),
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
        payload = {"source": source, "pb": None}
        for i, pollutant in enumerate(POLLUTANT_LIST):
            value = pollutant_values[i]
            payload[pollutant] = float(value) if value else None
        
        response = requests.post(f"{API_BASE_URL}/api/calculate_manual", json=payload)
        
        if response.status_code == 200:
            result = response.json()
            
            color_class = get_aqi_color_class(result['category'])
            
            result_message = html.Div([
                html.H2(f"AQI: {result['aqi']}", className=f"font-weight-bold {color_class}"),
                html.H4(f"({result['category']})", className=f"{color_class}"),
                html.P(f"Dominant: {result['dominant_pollutant'].upper()}", className="text-muted")
            ])
            return result_message, result 
        else:
            return dbc.Alert(f"API Error: {response.text}", color="danger"), dash.no_update
            
    except Exception as e:
        return dbc.Alert(f"An error occurred: {e}", color="danger"), dash.no_update

# Main callback to update the dashboard
@callback(
    [Output('stats-row', 'children'),
     Output('history-table-div', 'children'),
     Output('pollutant-chart', 'figure')],
    [Input('history-data-store', 'data')],
    prevent_initial_call=False
)
def update_dashboard_elements(new_data):
    """
    Fetches all data from the API and updates the history table, chart,
    and the stat cards.
    """
    try:
        api_url = f"{API_BASE_URL}/api/get_all_data"
        response = requests.get(api_url)
        data = response.json()
        
        # Default empty-state values
        stats_cards = [
            create_stat_card("Average AQI", "-", "avg-aqi-stat"),
            create_stat_card("Max AQI", "-", "max-aqi-stat"),
            create_stat_card("Std. Deviation", "-", "std-aqi-stat"),
            create_stat_card("Total Records", "-", "total-records-stat"),
        ]
        empty_table = html.P("No history data found. Use the calculator to add data!", className="text-muted")
        empty_fig = go.Figure().update_layout(
            template="plotly_dark",
            paper_bgcolor='#000000', plot_bgcolor='#000000', font={'color': 'white'},
            xaxis=dict(visible=False), yaxis=dict(visible=False)
        )
        
        if not data:
            return stats_cards, empty_table, empty_fig

        df = pd.DataFrame(data)
        
        # --- 1. NumPy Statistics ---
        aqi_values = df['aqi'].values  
        avg_aqi = np.mean(aqi_values)
        max_aqi = np.max(aqi_values)
        std_aqi = np.std(aqi_values)
        total_records = len(df)
        
        stats_cards = [
            create_stat_card("Average AQI (All Data)", f"{avg_aqi:.1f}", "avg-aqi-stat"),
            create_stat_card("Max AQI (All Data)", f"{max_aqi}", "max-aqi-stat"),
            create_stat_card("Std. Deviation", f"{std_aqi:.2f}", "std-aqi-stat"),
        
            create_stat_card("Total Records", f"{total_records}", "total-records-stat"),
        ]
        
        # 2. Timezone conversion for display
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['timestamp'] = df['timestamp'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')

        # 3. Create the History Table
        table_df = df[['timestamp', 'source', 'aqi', 'category', 'dominant_pollutant']].copy()
        table_df['timestamp'] = table_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        history_table = dash_table.DataTable(
            data=table_df.to_dict('records'),
            columns=[{'name': i.replace('_', ' ').title(), 'id': i} for i in table_df.columns],
            style_cell={'textAlign': 'left', 'backgroundColor': '#2b2b2b', 'color': 'white', 'border': '1px solid #444'},
            style_header={'backgroundColor': '#121212', 'fontWeight': 'bold'},
            style_table={'overflowY': 'auto', 'height': '400px'},
            page_size=10,
        )
        
        # 4. Create the Pollutant Chart
        chart_fig = build_pollutant_chart(df)

        return stats_cards, history_table, chart_fig

    except Exception as e:
        return stats_cards, dbc.Alert(f"Error loading history: {e}", color="danger"), empty_fig

# CSV Download callback
@callback(
    Output("download-csv", "data"),
    Input("btn-download-csv", "n_clicks"),
    prevent_initial_call=True,
)
def download_csv(n_clicks):
    """
    Downloads all data as a CSV.
    """
    api_url = f"{API_BASE_URL}/api/get_all_data?limit=9999"
    response = requests.get(api_url)
    all_data = response.json()
    df = pd.DataFrame(all_data)
    if not df.empty and 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
    return dcc.send_data_frame(df.to_csv, "aqi_history.csv", index=False)


# --- Custom CSS for new theme ---
# This injects a <style> tag into the app's <head>
app.clientside_callback(
    """
    function(n) {
        var style = document.createElement('style');
        style.innerHTML = `
            body {
                /* Blue-Green Gradient Background */
                background: linear-gradient(to bottom, #0a2e38, #000000) !important;
                background-attachment: fixed;
                color: #f0f0f0 !important;
            }
            .card {
                /* Semi-transparent cards */
                background-color: rgba(26, 26, 26, 0.8) !important; /* 80% opaque dark card */
                border: 1px solid #444444 !important;
                color: #f0f0f0 !important;
                border-radius: 15px !important; /* Rounded cards */
            }
            .card-header {
                /* Solid header for contrast */
                background-color: #121212 !important;
                border-bottom: 1px solid #444444 !important;
                font-weight: 600;
                border-top-left-radius: 15px !important;
                border-top-right-radius: 15px !important;
            }
            /* Style inputs */
            .form-control, .form-select {
                background-color: #1a1a1a !important;
                color: white !important;
                border-color: #444 !important;
                border-radius: 10px !important; /* Rounded inputs */
            }
            .form-control:focus, .form-select:focus {
                color: white !important;
                background-color: #1a1a1a !important;
                border-color: #0d6efd !important;
                box-shadow: 0 0 0 0.2rem rgba(13,110,253,.25) !important;
            }
            
            /* --- FIX: Rounded Buttons --- */
            .btn {
                border-radius: 20px !important; /* "Pill" shape */
                font-weight: 600 !important;
                padding: 0.5rem 1rem !important; /* A bit more padding */
            }
            
            /* --- FIX: Larger Table Font --- */
            .dash-table-container .dash-cell {
                border-color: #444 !important;
                font-size: 1.05rem !important; /* Increase font size */
                line-height: 1.5 !important;
            }
            .dash-table-container .dash-header {
                background-color: #121212 !important;
            }
            .dash-table-container .dash-data-row {
                background-color: #2b2b2b !important;
            }
        `;
        document.head.appendChild(style);
        return ""; // Return value doesn't matter
    }
    """,
    Output('dummy-output-for-css', 'children'),
    Input('dummy-input-for-css', 'children')
)

# --- Main execution ---
if __name__ == '__main__':
    app.run(debug=True, port=8050)