# frontend/dashboard.py
import dash
from dash import dcc, html, Input, Output, State, callback, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import requests
import pandas as pd
from dash_iconify import DashIconify

# --- CONFIGURATION ---
API_BASE_URL = "http://127.0.0.1:5000"
MAJOR_CITIES = [
    "New Delhi","Mumbai","Bengaluru","Chennai","Kolkata","Hyderabad","Pune","Ahmedabad",
    "Surat","Jaipur","Lucknow","Kanpur","Nagpur","Indore","Thane","Bhopal","Visakhapatnam",
    "Patna","Vadodara","Ghaziabad","Ludhiana","Agra","Nashik","Faridabad","Varanasi"
]

# Use a dark Bootstrap theme as a base (we override it with custom CSS)
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG], title="AQI Monitor")

# --- UTILS ---
def get_aqi_badge(category):
    # CPCB Standard Colors
    color_map = {
        "Good": "#4caf50",          # Green
        "Satisfactory": "#aeea00",  # Lime Green
        "Moderate": "#ffea00",      # Yellow
        "Poor": "#ff9100",          # Orange
        "Very Poor": "#ff1744",     # Red
        "Severe": "#b71c1c"         # Deep Maroon
    }
    
    bg_color = color_map.get(category, "#555555")
    
    # Using html.Span to guarantee the color is applied
    return html.Span(
        category.upper(), 
        style={
            "backgroundColor": bg_color,
            "color": "black" if category in ["Satisfactory", "Moderate"] else "white", # Smart text color
            "padding": "5px 15px",
            "borderRadius": "20px",
            "fontWeight": "bold",
            "fontSize": "1rem",
            "marginLeft": "10px",
            "display": "inline-block",
            "boxShadow": f"0 0 10px {bg_color}66" # Subtle glow for the badge too
        }
    )

def build_pollutant_chart(df):
    fig = go.Figure()
    
    # Ultra-clean dark chart theme
    layout_settings = dict(
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',   # Transparent outer container
        plot_bgcolor='#000000',          # <--- Solid Black Chart Background
        font={'family': "Inter, sans-serif", 'color': '#a0a0a0'},
        hovermode="x unified",
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis=dict(showgrid=True, gridcolor='#333333', zeroline=False, title="Time (IST)"), # Visible grid
        yaxis=dict(showgrid=True, gridcolor='#333333', zeroline=False),
        legend=dict(orientation="h", y=1.1),
        
        # Hover settings (Black Text on White Box)
        hoverlabel=dict(
            bgcolor="white",
            font_size=14,
            font_family="Inter",
            font_color="black"
        )
    )

    if df.empty:
        fig.update_layout(**layout_settings)
        fig.add_annotation(text="No Data Available", showarrow=False, font=dict(size=20, color="#555"))
        return fig

    # Convert to IST
    df_chart = df.copy()
    df_chart['timestamp'] = pd.to_datetime(df_chart['timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    df_chart = df_chart.sort_values('timestamp')

    pollutant_map = {
        'pm25_raw': 'PM2.5', 'pm10_raw': 'PM10', 'co_raw': 'CO',
        'no2_raw': 'NO2', 'so2_raw': 'SO2', 'o3_raw': 'O3'
    }

    # Neon colors
    colors = ['#00d2ff', '#3a7bd5', '#f12711', '#f5af19', '#93f9b9', '#89216b']
    
    for i, (key, name) in enumerate(pollutant_map.items()):
        if key in df_chart.columns and df_chart[key].notna().any():
            fig.add_trace(go.Scatter(
                x=df_chart['timestamp'], 
                y=df_chart[key],
                name=name,
                mode='lines+markers',        # <--- Markers added here
                marker=dict(size=6, symbol='circle'), # <--- 'o' Marker styling
                line=dict(width=2, color=colors[i % len(colors)]) # Removed fill
            ))

    fig.update_layout(**layout_settings)
    return fig

def create_stat_card(title, value, id_name, icon):
    return dbc.Col(dbc.Card(className="glass-card h-100", children=[
        dbc.CardBody([
            html.Div([
                DashIconify(icon=icon, width=24, className="text-muted mb-2"),
                html.H6(title, className="card-title text-muted text-uppercase small"),
            ]),
            html.H3(value, id=id_name, className="stat-value display-6")
        ])
    ]), md=3, className="mb-3")

# --- LAYOUT ---
app.layout = dbc.Container(fluid=True, className="p-4", children=[
    dcc.Store(id='history-data-store'),
    dcc.Download(id="download-csv"),
    dcc.Interval(id='auto-refresh-interval', interval=30*1000, n_intervals=0),

    # 1. Header Section
    dbc.Row(className="mb-5 text-center", children=[
        dbc.Col([
            html.H1([DashIconify(icon="ri:earth-line", className="me-3"), "AQI Monitor"], 
                    className="display-4 fw-bold text-white"),
            html.P("Real-time Air Quality Monitoring System", className="lead text-muted")
        ])
    ]),

    # 2. Controls Section (Floating Glass Bar)
    # --- FIX ADDED HERE: className="controls-row" ---
    dbc.Row(className="justify-content-center mb-5 controls-row", children=[
        dbc.Col(md=10, children=[
            dbc.Card(className="glass-card p-2", children=[
                dbc.CardBody(children=[
                    dbc.Row(align="center", children=[
                        dbc.Col(md=5, children=[
                            dcc.Dropdown(
                                id='city-dropdown',
                                options=[{"label": c, "value": c} for c in MAJOR_CITIES],
                                value="New Delhi",
                                placeholder="Select City...",
                                clearable=False,
                                className="text-dark"
                            )
                        ]),
                        dbc.Col(md=5, children=[
                            dbc.Input(id='custom-city-input', placeholder='Or type custom city...', type='text')
                        ]),
                        dbc.Col(md=2, children=[
                            dbc.Button([DashIconify(icon="bx:search", className="me-2"), "Fetch"], 
                                       id='btn-fetch-city', color="primary", className="w-100")
                        ])
                    ])
                ])
            ])
        ])
    ]),

    # 3. Live Status & Stats
    dbc.Row(className="mb-4", children=[
        # Left: Live Status
        dbc.Col(md=4, children=[html.Div(id='calc-output-div')]),
        
        # Right: Stats Grid
        dbc.Col(md=8, children=[
            dbc.Row(id='stats-row')
        ])
    ]),

    # 4. Chart Section
    dbc.Row(className="mb-4", children=[
        dbc.Col(md=12, children=[
            dbc.Card(className="glass-card", children=[
                dbc.CardHeader([DashIconify(icon="akar-icons:statistic-up", className="me-2"), "Pollutant Trends"]),
                dbc.CardBody(dcc.Graph(id='pollutant-chart', style={"height": "450px"}))
            ])
        ])
    ]),

    # 5. History Table (CENTERED)
    # --- FIX ADDED HERE: justify-content-center and md=10 ---
    dbc.Row(className="justify-content-center", children=[
        dbc.Col(md=10, lg=8, children=[  # Reduced width from 12 to 10/8 for a cleaner look
            dbc.Card(className="custom-table-card", children=[ # New class for styling
                dbc.CardHeader(html.Div([
                    html.Span([DashIconify(icon="bx:history", className="me-2"), "Recent Data Logs"]),
                    dbc.Button([DashIconify(icon="fa-solid:download"), " CSV"],
                               id="btn-download-csv", color="light", size="sm", outline=True,
                               className="float-end")
                ])),
                dbc.CardBody(html.Div(id='history-table-div'))
            ])
        ])
    ])
])

# --- UPDATED CALLBACKS ---

@callback(
    [Output('calc-output-div', 'children'), Output('history-data-store', 'data')],
    [Input('btn-fetch-city', 'n_clicks'), Input('city-dropdown', 'value')],
    [State('custom-city-input', 'value')],
    prevent_initial_call=True
)
def fetch_city_aqi(btn_clicks, selected_city, custom_city):
    ctx = dash.callback_context
    trigger = ctx.triggered[0]['prop_id'].split('.')[0]
    city = custom_city if (trigger == 'btn-fetch-city' and custom_city) else selected_city
    
    if not city: return dash.no_update, dash.no_update

    try:
        resp = requests.get(f"{API_BASE_URL}/api/fetch_city", params={"city": city}, timeout=10)
        if resp.status_code != 200:
            return dbc.Alert("API Error", color="danger"), dash.no_update
        
        data = resp.json()
        category = data.get('category')

        # Color map for the Big Number Glow
        color_map = {
            "Good": "#4caf50",
            "Satisfactory": "#aeea00",
            "Moderate": "#ffea00",
            "Poor": "#ff9100",
            "Very Poor": "#ff1744",
            "Severe": "#b71c1c"
        }
        aq_color = color_map.get(category, "#ffffff")

        card = dbc.Card(className="glass-card text-center h-100", children=[
            dbc.CardBody([
                html.H5(city.upper(), className="text-muted mb-3"),
                html.Div([
                    # Big AQI Number with Glow
                    html.H1(
                        data.get('aqi'), 
                        className="display-1 fw-bold mb-0",
                        style={
                            "color": aq_color, 
                            "textShadow": f"0 0 30px {aq_color}66"
                        }
                    ),
                    # The fixed badge function
                    get_aqi_badge(category)
                ], className="mb-3"),
                
                html.Hr(className="my-3", style={"borderColor": "rgba(255,255,255,0.2)"}),

                dbc.Row([
                    dbc.Col([html.Small("PM2.5"), html.H5(data.get('pm25_raw'), className="text-info")]),
                    dbc.Col([html.Small("PM10"), html.H5(data.get('pm10_raw'), className="text-warning")]),
                    dbc.Col([html.Small("NO2"), html.H5(data.get('no2_raw'), className="text-success")]),
                ]),
                
                dbc.Row(className="mt-4", children=[
                    dbc.Col([
                        html.Small("Dominant Pollutant", className="text-muted"),
                        # --- GLOW IS BACK HERE ---
                        html.H3(
                            str(data.get('dominant_pollutant')).upper(), 
                            style={
                                'color': '#ff3333', 
                                'fontWeight': '800',
                                'textShadow': '0 0 15px rgba(255, 51, 51, 0.6)' # Red Glow
                            }
                        )
                    ]),
                ])
            ])
        ])
        return card, data
    except Exception as e:
        return dbc.Alert(f"Error: {e}", color="danger"), dash.no_update

@callback(
    [Output('stats-row', 'children'), Output('history-table-div', 'children'), Output('pollutant-chart', 'figure')],
    [Input('auto-refresh-interval', 'n_intervals'), Input('history-data-store', 'data'), Input('city-dropdown', 'value')]
)
def update_dashboard(n, new_data, dropdown_city):
    try:
        data = requests.get(f"{API_BASE_URL}/api/get_all_data", timeout=5).json()
    except: data = []
    
    # Filter
    target = new_data.get('source') if (new_data and 'source' in new_data) else f"OpenWeatherMap:{dropdown_city}"
    df = pd.DataFrame(data)
    if not df.empty: df = df[df['source'] == target]

    if df.empty:
        stats = [create_stat_card("Waiting...", "-", f"s{i}", "bx:loader") for i in range(4)]
        return stats, html.P("No records found", className="text-center text-muted"), build_pollutant_chart(pd.DataFrame())

    # Stats
    stats = [
        create_stat_card("Avg AQI", f"{df['aqi'].mean():.0f}", "stat-avg", "bx:bar-chart-alt-2"),
        create_stat_card("Max AQI", f"{df['aqi'].max()}", "stat-max", "bx:trending-up"),
        create_stat_card("Dominant", str(df['dominant_pollutant'].mode()[0]).upper(), "stat-dom", "bx:atom"),
        create_stat_card("Records", str(len(df)), "stat-cnt", "bx:data"),
    ]

    # Chart & Table
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    
    # --- FIXED: ADDED ALL COLUMNS TO TABLE ---
    # We define the columns we want to see
    cols_to_show = ['timestamp', 'aqi', 'category', 'dominant_pollutant', 'pm25_raw', 'pm10_raw', 'no2_raw', 'co_raw']
    
    table = dash_table.DataTable(
        data=df.sort_values('timestamp', ascending=False).to_dict('records'),
        columns=[{"name": i.replace('_raw', '').replace('_', ' ').upper(), "id": i} for i in cols_to_show],
        style_header={'backgroundColor': 'rgba(0,0,0,0.5)', 'color': 'white', 'border': 'none', 'fontWeight': 'bold'},
        style_cell={'backgroundColor': 'rgba(255,255,255,0.05)', 'color': '#ddd', 'border': '1px solid #444', 'textAlign': 'center'},
        page_size=10
    )
    
    return stats, table, build_pollutant_chart(df)

@callback(
    Output("download-csv", "data"),
    Input("btn-download-csv", "n_clicks"),
    State("city-dropdown", "value"),
    prevent_initial_call=True
)
def download_csv(n, city):
    try:
        df = pd.DataFrame(requests.get(f"{API_BASE_URL}/api/get_all_data").json())
        df = df[df['source'] == f"OpenWeatherMap:{city}"]
        return dcc.send_data_frame(df.to_csv, f"aqi_{city}.csv")
    except: return dash.no_update

if __name__ == '__main__':
    app.run(debug=True, port=8050)