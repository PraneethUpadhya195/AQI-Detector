import dash
from dash import dcc, html, Input, Output, State, callback, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import requests
import pandas as pd
from datetime import datetime
from dash_iconify import DashIconify
import numpy as np  # <-- EXPLICIT NUMPY IMPORT

# --- Configuration ---
API_BASE_URL = "http://127.0.0.1:5000"
POLLUTANT_LIST = ['pm25', 'pm10', 'co', 'no2', 'so2', 'o3', 'nh3']

# --- App Initialization ---
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# --- Helper Functions ---
def get_aqi_color_class(category):
    """Returns a Bootstrap text color class based on the AQI category."""
    mapping = {
        "Good": "text-success",
        "Satisfactory": "text-success-light",
        "Moderate": "text-warning",
        "Poor": "text-danger-light",
        "Very Poor": "text-danger",
        "Severe": "text-danger-severe",
    }
    return mapping.get(category, "text-white")

def build_pollutant_chart(df):
    """Builds the main pollutant chart with a dark theme."""
    fig = go.Figure()
    df_chart = df.iloc[::-1] # Reverse for plotting
    pollutant_display_names = {
        'pm25_raw': 'PM2.5', 'pm10_raw': 'PM10', 'co_raw': 'CO',
        'no2_raw': 'NO2', 'so2_raw': 'SO2', 'o3_raw': 'O3',
        'nh3_raw': 'NH3', 'pb_raw': 'Lead (Pb)'
    }
    for key, display_name in pollutant_display_names.items():
        if key in df_chart.columns and df_chart[key].notna().any():
            fig.add_trace(go.Trace(
                x=df_chart['timestamp'], y=df_chart[key], 
                name=display_name, mode='lines+markers'
            ))
    fig.update_layout(
        paper_bgcolor='#000000', plot_bgcolor='#000000',
        font={'color': 'white'}, legend_title_text='Pollutants',
        xaxis_title="Timestamp (IST)", yaxis_title="Concentration"
    )
    return fig

# --- NEW HELPER FUNCTION ---
def create_stat_card(title, value, color):
    """Creates a small card for the new statistics row."""
    return dbc.Col(
        dbc.Card(
            dbc.CardBody([
                html.H6(title, className="card-title text-white"),
                html.H3(value, className=f"card-text font-weight-bold {color}")
            ]),
            className="shadow-sm",
            style={'backgroundColor': '#1a1a1a', 'border': '1px solid #222'}
        ),
        md=4
    )

# --- App Layout ---
app.layout = html.Div(style={
    'background': 'linear-gradient(to bottom, #0a2e38, #000000)',
    'minHeight': '100vh',
    'color': 'white'
}, children=[
    dcc.Store(id='history-data-store'),
    dcc.Download(id="download-csv"),
    html.Div(id='dummy-input-for-css', style={'display': 'none'}),
    html.Div(id='dummy-output-for-css', style={'display': 'none'}),

    dbc.Container(fluid=True, children=[
        # Main Title
        dbc.Row([
            dbc.Col(html.H1("Manual AQI Calculator & Data Logger", className="text-center my-4"))
        ]),
        
        # --- NEW: Statistical Overview Row ---
        dbc.Row(id='stats-row', className="mb-4 justify-content-center", children=[
            # This row will be populated by the callback
            create_stat_card("Average AQI", "-", "text-white"),
            create_stat_card("Max AQI", "-", "text-white"),
            create_stat_card("Std. Deviation", "-", "text-white"),
        ]),
        # --- END OF NEW SECTION ---

        # --- Row 1: Chart and Table ---
        dbc.Row([
            dbc.Col(md=7, children=[
                dbc.Card(className="shadow", children=[
                    dbc.CardHeader(html.H4("Pollutant History")),
                    dbc.CardBody(dcc.Graph(
                        id='pollutant-chart',
                        config={'scrollZoom': True, 'displaylogo': False}
                    ))
                ], style={'backgroundColor': '#1a1a1a', 'border': '1px solid #222'})
            ]),
            dbc.Col(md=5, children=[
                dbc.Card(className="shadow", children=[
                    dbc.CardHeader(html.H4(children=[
                        "Data History",
                        dbc.Button(
                            DashIconify(icon="fa-solid:download", width=20),
                            id="btn-download-csv", color="primary",
                            className="float-end", size="sm"
                        )
                    ])),
                    dbc.CardBody(html.Div(id='history-table-div'))
                ], style={'backgroundColor': '#1a1a1a', 'border': '1px solid #222'})
            ]),
        ]),
        
        # --- Row 2: The Calculator ---
        dbc.Row(className="mt-5 justify-content-center", children=[
            dbc.Col(md=10, children=[
                dbc.Card(className="shadow", children=[
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
                ], style={'backgroundColor': '#1a1a1a', 'border': '1px solid #222'})
            ])
        ])
    ])
])

# --- Callbacks ---

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
                html.H4(f"({result['category']})", className=f" {color_class}"),
                html.P(f"Dominant: {result['dominant_pollutant'].upper()}")
            ])
            return result_message, result 
        else:
            return dbc.Alert(f"API Error: {response.text}", color="danger"), dash.no_update
            
    except Exception as e:
        return dbc.Alert(f"An error occurred: {e}", color="danger"), dash.no_update

@callback(
    [Output('stats-row', 'children'),           # <-- NEW OUTPUT
     Output('history-table-div', 'children'),
     Output('pollutant-chart', 'figure')],
    [Input('history-data-store', 'data')],
    prevent_initial_call=False
)
def update_history_chart_and_stats(new_data):
    """
    Fetches all data from the API and updates the history table, chart,
    AND the new NumPy-powered stat cards.
    """
    try:
        api_url = f"{API_BASE_URL}/api/get_all_data"
        response = requests.get(api_url)
        data = response.json()
        
        # Default empty-state values
        stats_cards = [
            create_stat_card("Average AQI", "-", "text-white"),
            create_stat_card("Max AQI", "-", "text-white"),
            create_stat_card("Std. Deviation", "-", "text-white"),
        ]
        empty_table = html.P("No history data found. Calculate an AQI to get started!")
        empty_fig = go.Figure().update_layout(
            paper_bgcolor='#000000', plot_bgcolor='#000000', font={'color': 'white'}
        )
        
        if not data:
            return stats_cards, empty_table, empty_fig

        df = pd.DataFrame(data)
        
        # --- 1. *** NEW: EXPLICIT NUMPY CALCULATION *** ---
        # We get the 'aqi' column from the DataFrame. 
        # .values returns the underlying NumPy array.
        aqi_values = df['aqi'].values  
        
        # Now we use NumPy's functions on the array
        avg_aqi = np.mean(aqi_values)
        max_aqi = np.max(aqi_values)
        std_aqi = np.std(aqi_values)
        
        # Create the new stat cards
        stats_cards = [
            create_stat_card("Average AQI (All Data)", f"{avg_aqi:.1f}", "text-primary"),
            create_stat_card("Max AQI (All Data)", f"{max_aqi}", "text-danger"),
            create_stat_card("Std. Deviation", f"{std_aqi:.2f}", "text-warning"),
        ]
        # --- END OF NUMPY SECTION ---

        # 2. Timezone conversion for display
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['timestamp'] = df['timestamp'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')

        # 3. Create the History Table
        table_df = df[['timestamp', 'source', 'aqi', 'category', 'dominant_pollutant']].copy()
        table_df['timestamp'] = table_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        history_table = dash_table.DataTable(
            data=table_df.to_dict('records'),
            columns=[{'name': i.replace('_', ' ').title(), 'id': i} for i in table_df.columns],
            style_cell={'textAlign': 'left', 'backgroundColor': '#333', 'color': 'white'},
            style_header={'backgroundColor': '#111', 'fontWeight': 'bold'},
            style_table={'overflowY': 'auto', 'height': '400px'},
            page_size=10,
        )
        
        # 4. Create the Pollutant Chart
        chart_fig = build_pollutant_chart(df)

        return stats_cards, history_table, chart_fig

    except Exception as e:
        return stats_cards, dbc.Alert(f"Error loading history: {e}", color="danger"), empty_fig

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
app.clientside_callback(
    """
    function(n) {
        var style = document.createElement('style');
        style.innerHTML = `
            body {
                background: linear-gradient(to bottom, #0a2e38, #000000) !important;
                background-attachment: fixed;
            }
            .card {
                background-color: rgba(26, 26, 26, 0.8) !important;
                border: 1px solid #222 !important;
                color: white !important;
            }
            .card-header {
                background-color: rgba(0, 0, 0, 0.3) !important;
                border-bottom: 1px solid #222 !important;
            }
            .dash-table-container .dash-header, 
            .dash-table-container .dash-data-row {
                background-color: #333 !important;
                color: white !important;
            }
            .dash-table-container .dash-header {
                background-color: #111 !important;
                font-weight: bold !important;
            }
            .dash-table-container .dash-cell { border-color: #555 !important; }
            .text-success-light { color: #a0d64a !important; }
            .text-danger-light { color: #f28e2c !important; }
            .text-danger-severe { color: #760013 !important; }
        `;
        document.head.appendChild(style);
        return "";
    }
    """,
    Output('dummy-output-for-css', 'children'),
    Input('dummy-input-for-css', 'children')
)

# --- Main execution ---
if __name__ == '__main__':
    app.run(debug=True, port=8050)