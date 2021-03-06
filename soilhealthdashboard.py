import pandas as pd
import ast
import re
import plotly.express as px
from dash import Dash, dcc, html, Input, Output
from dash.dependencies import State
from dash.exceptions import PreventUpdate
import os
import webbrowser
import json

#some housekeeping
#os.chdir(os.path.dirname(os.path.abspath(__file__))) #in order to keep the file structure intact

# input_files#
data_file = "20211207_combined_files.txt"
df = pd.read_csv(data_file, sep=',')  #get the data to create the map
df = df.drop_duplicates(ignore_index = True)

app = Dash(__name__)
server = app.server
# ------------------------------------------------------------------------------
# App layout
app.layout = html.Div([

    dcc.Store(id='session'),
    html.Div(
        style={'display': 'flex'},
        children = [
            html.Div(
                style = {'flex': '15%'},
                children = [
                    html.H2("SquaredAnt Soil Health Dashboard", style={'text-align': 'left'}),
                    dcc.Dropdown(id="slct_year",
                    options=[
                         {"label": "2015", "value": 2015},
                         {"label": "2016", "value": 2016},
                         {"label": "2017", "value": 2017},
                         {"label": "2018", "value": 2018},
                         {"label": "2019", "value": 2019},
                         {"label": "2020", "value": 2020},
                         {"label": "2021", "value": 2021},
                         {"label": "All", "value": "all years"}],
                        multi=False,
                        value="all years",
                        style={'width': "100%"}
                    ),
                    html.Div(id='year_container', children=[]),
                    dcc.Dropdown(id="slct_type",
                        options=[
                            {"label": "Pollution", "value": 'Pollution'},
                            {"label": "Degradation", "value": 'Degradation'}
                        ],
                        multi=False,
                        value="Pollution",
                        style={'width': "100%"}
                    ),
                    html.Div(id='type_container', children=[]),
                    html.Br(),
                ],
            ),
            html.Div(
                style = {'flex': '80%'},
                children = [
                    html.H4("map of microbiome-based soil health indications"),
                    html.Div(
                        children = [
                            html.Div(
                                children = dcc.Graph(
                                    id='my_soil_map',
                                    figure={}
                                ),
                                style={'width': '100%', 'display': 'inline-block'}
                            )
                        ]
                    ),
                ],
            ),
        ],
    ),
    html.Div(
        style={'display': 'flex'},
        children = [
            html.Div(
                style = {'flex': '50%'},
                children = [
                    html.H4("Historical data"),
                    html.Div(
                        children = dcc.Graph(
                            id='my_history',
                            figure={}
                        )
                    ),
                ],
            ),
            html.Div(
                style = {'flex': '50%'},
                children = [
                    html.H4("Link to original data"),
                    html.A(
                        children="no link",
                        id="data_link",
                        href="",
                        target="_blank",
                        style={'text-align:': 'center'}
                    ),
                    html.H4("Top taxa on selected location"),
                    html.Div(
                        children = dcc.Graph(
                            id='my_topten',
                            figure={}
                        )
                    ),
                ],
            )
        ],
    )
])


# ------------------------------------------------------------------------------
# Connect the Plotly graphs with Dash Components

@app.callback(
    [Output('session','data'),
     Output(component_id='year_container', component_property='children'),
     Output(component_id='type_container', component_property='children')
    ],
    [Input(component_id='slct_year', component_property='value'),
     Input(component_id='slct_type', component_property='value'),
     Input(component_id='year_container', component_property='children'),
     Input(component_id='type_container', component_property='children')
    ],
    State('session', 'data')
)
def update_graph(year_slctd, type_slctd, prev_year, prev_type, stored):

    dff= pd.DataFrame()
    if (stored != None):
        dff = json.loads(stored)
        dff = pd.DataFrame(dff)

    else:
        dff = df.copy()
    print("check")
    print (dff)

    # prepare the data
    type_slctd = str(type_slctd)
    container_year = "Data for: {}".format(year_slctd)
    container_type = "Data for: {}".format(type_slctd)

    if (prev_type != container_type or prev_year != container_year):

        dff = df.copy() #make again

        if (year_slctd != "all years"):
            dff = dff[dff["Year"] == str(year_slctd)]

        #collect the IDs based on the coordinates
        dff_names = dff.drop_duplicates(subset=['Lat','Lon']) #use ID, Lat, Lon
        dff_names = dff_names.drop(['Pollution', 'Degradation'], axis = 1)
        dff_names['link'] = 'link'

        #get an avarage of all scores for those on the same location
        dff_top10 = dff.groupby(['Lat', 'Lon'], as_index=False)
        dff_topten_out = pd.DataFrame()
        for tt in dff_top10:
            tt1_df = tt[1]
            this_lat = tt1_df.iloc[0]['Lat']
            this_lon = tt1_df.iloc[0]['Lon']
            rows = pd.DataFrame()
            #print (tt1_df.shape[0])
            #print(range(tt1_df.shape[0]))
            for i in range(int(tt1_df.shape[0])):
                #print (i)
                tt_i = tt1_df.iloc[i]['Topten']
                tt_dict = ast.literal_eval(tt_i) #get the firs layer of "nest"
                #print(tt_dict)
                tt_df = pd.DataFrame(tt_dict)
                #tt_df = tt_df.iloc[:,0].to_string(index = False)  #get the second layer of "nest"
                #tt_dict = ast.literal_eval(tt_df)
                #tt_df = pd.DataFrame([tt_dict])
                rows = rows.append(tt_df.T,ignore_index=True)
            topten_avg = rows.mean().to_json()
            #print (topten_avg)
            #store this in the dff_topten_out dataframe
            dff_topten_out = dff_topten_out.append({'Lat': this_lat, 'Lon': this_lon , 'tt_average': topten_avg}, ignore_index=True)


        #get an avarage of all scores for those on the same location
        dff = dff.groupby(['Lat', 'Lon'], as_index=False).mean()[['Lat', 'Lon', type_slctd]]
        dff[type_slctd] = dff[type_slctd].round(2)

        #merge the IDs
        dff = pd.merge(dff, dff_names, on=['Lat', 'Lon'], how='left')
        dff = pd.merge(dff, dff_topten_out, on=['Lat', 'Lon'], how='left')


        #we also need alpha diversity
        dff_alpha = 7
        dff['alpha'] = dff_alpha

        print(dff['tt_average'])

    #close the shop
    return dff.to_json(), container_year, container_type


@app.callback(
    [Output(component_id='my_soil_map', component_property='figure'),
     Output(component_id='my_topten', component_property='figure'),
     Output(component_id='my_history', component_property='figure'),
     Output(component_id='my_soil_map', component_property='clickData'),
     Output(component_id='data_link', component_property='children'),
     Output(component_id='data_link', component_property='href')
     ],
    [Input('session', 'data'),
    Input('my_soil_map', 'clickData'),
    Input(component_id='slct_type', component_property='value')
    ]
)
def make_figures(data, clickData, type_slctd):


    #define variables to return
    clicked = "no selection"
    url = None
    top_rank_barplot = px.bar(pd.DataFrame([{'no clicked data':0}]), barmode="group")
    historical_data_plot = px.bar(pd.DataFrame([{'no clicked data':0}]), barmode="group")
    center_lon = 0
    center_lat = 0
    zoom = 1
    dff = pd.DataFrame()
    if (data != None):
        dff = json.loads(data)
        dff = pd.DataFrame(dff)
        print(dff)
    else:
        dff = df.copy()


    # check if we need to link out
    if clickData != None:
        url = clickData
        this_id = (url['points'][0]['customdata'][1])
        center_lon = url['points'][0]['lon']
        center_lat =  url['points'][0]['lat']
        zoom = 11
        url = 'https://www.ncbi.nlm.nih.gov/sra/' + (url['points'][0]['customdata'][1])
        clicked = url
        matching_index = dff.index[dff['ID'] == this_id].tolist()
        send_this = dff['tt_average'][matching_index[0]]
        top_rank_barplot = topGraph(send_this)
        historic_data = df[(df['Lat']==center_lat) & (df['Lon'] == center_lon)]
        historical_data_plot = historyPlot(historic_data)
        del(url)


    # Plotly Express
    fig = px.scatter_mapbox(dff, lat="Lat", lon="Lon", color=type_slctd, custom_data = ('link',), hover_data=['ID',type_slctd],range_color=[0, 1], zoom=zoom, height=400,  color_continuous_scale=['green', 'orange'])
    fig.update_layout(mapbox_style= "open-street-map")
    fig.update_layout(mapbox_pitch= 15)
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    fig.update_layout(
        hoverlabel=dict(
            bgcolor="white",
            font_size=15,
        )
    )
    fig.update_traces(marker={'size': 10})
    fig.update_layout(mapbox_center ={'lat':center_lat, 'lon':center_lon})


    return fig, top_rank_barplot, historical_data_plot, None, clicked, clicked






class topten:
    def __init__(self, top):
        self._top = top

    @property
    def top(self):
        return self._top



def topGraph(taxa):
    #dict = taxa.top
    tt = json.loads(taxa)
    tt_df = pd.DataFrame([tt])
    tt_df = tt_df.sort_values(by = 0,  axis=1, ascending=False)
    tt_df = tt_df.T
    tt_df = tt_df.reset_index()
    tt_df.columns = ['taxa', 'percentage']

    print(tt_df)
    this_fig = px.bar(tt_df, x = 'taxa', y = 'percentage', barmode="group", log_y=True, hover_data=['taxa', 'percentage'], text='taxa')
    this_fig.update_xaxes(tickangle=90)
    return (this_fig)

def historyPlot(data):
    #first summarize per year per pollution or degradation
    data_grouped_pollution  = data.groupby('Year').agg({'Pollution': ['mean', 'min', 'max']})
    data_grouped_pollution= data_grouped_pollution['Pollution']
    data_grouped_pollution.reset_index(inplace=True)
    data_grouped_pollution['Indicator'] = 'Pollution'
    print (data_grouped_pollution)
    data_grouped_degradation  = data.groupby('Year').agg({'Degradation': ['mean', 'min', 'max']})
    data_grouped_degradation= data_grouped_degradation['Degradation']
    data_grouped_degradation.reset_index(inplace=True)
    data_grouped_degradation['Indicator'] = 'Degradation'
    print (data_grouped_degradation)
    data_grouped = pd.concat([data_grouped_pollution, data_grouped_degradation], axis = 0)
    print (data_grouped)
    this_fig = px.bar(data_grouped, x="Year", y="mean", color='Indicator',  barmode="group")
    this_fig.update_yaxes(range=[0, 1])
    return this_fig



# ------------------------------------------------------------------------------
if __name__ == '__main__':
    app.run_server(debug=True, threaded=True)
