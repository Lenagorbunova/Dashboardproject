import dash
from dash import html, dcc, dash_table
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from sqlalchemy import create_engine


# Загрузка данных о странах
engine = create_engine('postgresql://postgres:123@localhost:5432/postgres')
df_countries = pd.read_sql_query("SELECT * FROM geo_info.countries", engine)

# Загрузка CSV с рисками
risk_df = pd.read_csv('materials/risks.csv', encoding='cp1251', sep=';', skipinitialspace=True)
risk_df.columns = risk_df.columns.str.strip()

# Загрузка данных для графиков
daily_stats_df = pd.read_excel('materials/daily_statistics.xlsx')

# Загрузка координат стран
coord_df = pd.read_excel('materials/countries_coord.xlsx')


# Функция для преобразования чисел с запятой в float
def convert_comma_to_float(value):
    if isinstance(value, str):
        return float(value.replace(',', '.'))
    return value


# Применяем преобразование ко всем колонкам кроме ID страны
for col in risk_df.columns:
    if col != 'ID страны':
        risk_df[col] = risk_df[col].apply(convert_comma_to_float)

# Конфигурации для таблиц
config = {
    'name': ('Название страны', str),
    'iso2': ('Код ISO-2', str),
    'iso3': ('Код ISO-3', str),
    'population': ('Население', lambda x: f"{int(x):,}".replace(',', ' ')),
    'density': ('Плотность', lambda x: f"{float(x):.2f}"),
    'prop_population_65': ('Доля > 65 лет', lambda x: f"{float(x):.2f}%"),
    'prop_population_f': ('Доля женщин', lambda x: f"{float(x):.2f}%")
}

distribution_config = {
    'diabetes': ('Диагностированный диабет (>= 18 лет)', lambda x: f"{float(x):.1f}%"),
    'obesity': ('Ожирение (индекс массы тела 30+)', lambda x: f"{float(x):.1f}%"),
    'smoking': ('Курение', lambda x: f"{float(x):.1f}%"),
    'copd': ('ХОБЛ', lambda x: f"{float(x):.2f}%"),
    'cvd': ('Сердечно-сосудистые заболевания', lambda x: f"{float(x):.2f}%"),
    'hiv': ('ВИЧ/СПИД', lambda x: f"{float(x):.2f}%"),
    'hypertension': ('Гипертония', lambda x: f"{float(x):.2f}%")
}

risk_config = {
    'Риск общий': ('Общий риск', lambda x: f"{float(x):.2%}"),
    'Риск по возрасту': ('Риск по возрасту', lambda x: f"{float(x):.2%}"),
    'Высокий риск госпитализации': ('Высокий риск госпитализации', lambda x: f"{float(x):.2%}")
}

# Создаем dropdown для стран
countries_names_for_dropdown = [{'label': x, 'value': x} for x in df_countries['name']]

# Подготовка данных для карты
# Объединяем данные о случаях с координатами стран
daily_stats_df['observed_date'] = pd.to_datetime(daily_stats_df['observed_date'])
coord_df['name'] = coord_df['name'].str.strip()
daily_stats_df['name'] = daily_stats_df['name'].str.strip()

# Находим минимальную и максимальную даты для календаря
min_date = daily_stats_df['observed_date'].min()
max_date = daily_stats_df['observed_date'].max()


# Генерируем уникальные цвета для каждой страны
def generate_country_colors(country_names):
    colors = {}
    # Используем цветовую палитру Plotly
    base_colors = px.colors.qualitative.Set1 + px.colors.qualitative.Set2 + px.colors.qualitative.Set3 + px.colors.qualitative.Pastel1 + px.colors.qualitative.Pastel2

    for i, country in enumerate(country_names):
        # Циклически используем цвета из палитры
        color_idx = i % len(base_colors)
        colors[country] = base_colors[color_idx]

    return colors


# Получаем список всех стран из координат
all_countries = coord_df['name'].unique().tolist()
country_colors = generate_country_colors(all_countries)

# Стили для таблиц
table_style = {
    'width': '350px',
    'border': '1px solid #ddd',
    'borderTop': 'none',
    'margin': '0 auto'
}

cell_style = {
    'textAlign': 'left',
    'padding': '8px',
    'border': '1px solid #ddd',
    'fontSize': '12px',
    'backgroundColor': 'white',
    'overflow': 'hidden',
    'textOverflow': 'ellipsis',
    'maxWidth': '200px'
}

header_style = {
    'backgroundColor': 'white',
    'color': 'black',
    'fontWeight': 'bold',
    'padding': '10px',
    'textAlign': 'center',
    'fontSize': '14px',
    'border': '1px solid #ddd',
    'borderBottom': 'none'
}

# Создаем приложение Dash
app = dash.Dash(__name__, title="Дашборд протекания пандемии COVID-19")
app.layout = html.Div([
    # Заголовок
    html.H1(
        "Дашборд протекания пандемии COVID-19",
        style={
            'textAlign': 'center',
            'fontSize': '24px',
            'marginBottom': '20px',
            'color': '#2c3e50'
        }
    ),

    # Вкладки
    dcc.Tabs(id='tabs', value='tab-map', children=[
        dcc.Tab(label='Карта мира', value='tab-map'),
        dcc.Tab(label='Информация по стране', value='tab-country')
    ], style={
        'fontSize': '16px',
        'fontWeight': 'bold'
    }),

    # Контейнер для содержимого вкладок
    html.Div(id='tabs-content')
])


# Callback для переключения вкладок
@app.callback(
    Output('tabs-content', 'children'),
    [Input('tabs', 'value')]
)
def render_content(tab):
    if tab == 'tab-map':
        return html.Div([
            # Выбор даты для карты
            html.Div([
                html.Label('Выберите дату:',
                           style={'fontWeight': 'bold', 'marginBottom': '10px', 'fontSize': '16px'}),
                dcc.DatePickerSingle(
                    id='date-picker',
                    min_date_allowed=min_date,
                    max_date_allowed=max_date,
                    date=min_date,
                    display_format='DD.MM.YYYY',
                    style={'marginBottom': '20px'}
                )
            ], style={'width': '30%', 'margin': '0 auto 30px auto'}),

            # Карта мира с легендой
            html.Div([
                html.Div([
                    dcc.Graph(
                        id='world-map',
                        style={'height': '75vh', 'width': '80%', 'display': 'inline-block'}
                    ),
                    # Легенда для карты
                    html.Div(
                        id='map-legend',
                        style={
                            'width': '18%',
                            'height': '75vh',
                            'display': 'inline-block',
                            'verticalAlign': 'top',
                            'overflowY': 'auto',
                            'border': '1px solid #ddd',
                            'padding': '10px',
                            'marginLeft': '10px',
                            'backgroundColor': '#f9f9f9'
                        }
                    )
                ], style={'display': 'flex', 'width': '100%'})
            ])
        ])

    elif tab == 'tab-country':
        return html.Div([
            # Выбор страны
            html.Div([
                html.Label('Выберите страну:',
                           style={'fontWeight': 'bold', 'marginBottom': '10px', 'fontSize': '16px'}),
                dcc.Dropdown(
                    id='country-dropdown',
                    options=countries_names_for_dropdown,
                    value='Russia',
                    clearable=False,
                    style={'width': '100%'}
                )
            ], style={'width': '30%', 'margin': '0 auto 30px auto'}),

            # Контейнер для таблиц
            html.Div(id='tables-container', style={'marginBottom': '40px'}),

            # Контейнер для графиков
            html.Div(id='graphs-container')
        ])


# Callback для обновления карты и легенды
@app.callback(
    [Output('world-map', 'figure'),
     Output('map-legend', 'children')],
    [Input('date-picker', 'date')]
)
def update_world_map(selected_date):
    if selected_date is None:
        selected_date = min_date

    # Преобразуем дату в нужный формат
    selected_date_obj = pd.to_datetime(selected_date)

    # Фильтруем данные по выбранной дате
    date_data = daily_stats_df[daily_stats_df['observed_date'] == selected_date_obj].copy()

    # Объединяем с координатами стран
    map_data = pd.merge(date_data, coord_df, on='name', how='left')

    # Удаляем страны без координат
    map_data = map_data.dropna(subset=['longitude', 'latitude'])

    # Создаем легенду
    legend_items = []

    if not map_data.empty:
        # Добавляем цвет для каждой страны в данных
        map_data['country_color'] = map_data['name'].apply(lambda x: country_colors.get(x, '#808080'))

        # Используем подтвержденные случаи на 100к населения для размера кругов
        # Добавляем небольшое значение, чтобы избежать нулевых размеров
        map_data['size_value'] = map_data['confirmed_per_100k'].fillna(0) + 1

        # Создаем карту с помощью plotly.graph_objects для большего контроля
        fig = go.Figure()

        # Группируем данные по странам для создания отдельных traces
        for idx, row in map_data.iterrows():
            country_name = row['name']
            country_color = row['country_color']

            fig.add_trace(go.Scattergeo(
                lon=[row['longitude']],
                lat=[row['latitude']],
                mode='markers',
                marker=dict(
                    size=max(5, min(50, row['size_value'])),  # Ограничиваем размер
                    color=country_color,
                    opacity=0.8,
                    line=dict(width=1, color='darkgray'),
                    sizemode='area'
                ),
                name=country_name,
                text=f"{country_name}<br>Случаев на 100к: {row['confirmed_per_100k']:.2f}<br>Смертей на 100к: {row['deaths_per_100k']:.2f}",
                hoverinfo='text',
                showlegend=False  # Не показывать в легенде Plotly, так как у нас своя
            ))

            # Добавляем элемент в кастомную легенду
            legend_items.append(
                html.Div([
                    html.Span(
                        "●",
                        style={
                            'color': country_color,
                            'fontSize': '20px',
                            'marginRight': '8px'
                        }
                    ),
                    html.Span(
                        f"{country_name}",
                        style={'fontSize': '12px'}
                    ),
                    html.Br(),
                    html.Span(
                        f"Случаев: {row['confirmed_per_100k']:.1f}",
                        style={'fontSize': '10px', 'color': '#666', 'marginLeft': '28px'}
                    )
                ], style={'marginBottom': '5px', 'padding': '3px'})
            )

        # Настраиваем оформление карты
        fig.update_geos(
            showcountries=True,
            countrycolor="lightgray",
            showocean=True,
            oceancolor="#E0F7FA",
            showland=True,
            landcolor="white",
            showcoastlines=True,
            coastlinecolor="gray",
            projection_type="natural earth"
        )

        fig.update_layout(
            height=700,
            title=dict(
                text=f'Распространение COVID-19 на {selected_date_obj.strftime("%d.%m.%Y")}',
                x=0.5,
                font=dict(size=20)
            ),
            margin=dict(l=0, r=0, t=50, b=0),
            geo=dict(
                showframe=False,
                showcoastlines=True,
                projection_type='natural earth',
                landcolor='white',
                bgcolor='#E0F7FA'
            )
        )

        # Добавляем аннотацию для пояснения
        fig.add_annotation(
            x=0.02,
            y=0.02,
            xref="paper",
            yref="paper",
            text="Размер круга показывает количество подтвержденных случаев на 100 тысяч населения",
            showarrow=False,
            font=dict(size=12),
            bgcolor="white",
            bordercolor="black",
            borderwidth=1,
            borderpad=4
        )

    else:
        # Если нет данных на выбранную дату, создаем пустую карту
        fig = go.Figure()
        fig.update_geos(
            showcountries=True,
            countrycolor="lightgray",
            showocean=True,
            oceancolor="#E0F7FA",
            showland=True,
            landcolor="white"
        )
        fig.update_layout(
            title=dict(
                text=f'Нет данных на {selected_date_obj.strftime("%d.%m.%Y")}',
                x=0.5
            ),
            height=700
        )
        legend_items = [html.Div("Нет данных для отображения", style={'color': 'red'})]

    # Создаем заголовок для легенды
    legend_header = html.Div([
        html.H4("Легенда карты", style={'marginBottom': '10px', 'textAlign': 'center'}),
        html.Hr(style={'marginBottom': '10px'}),
        html.Div([
            html.Span("●", style={'color': '#FF4B4B', 'fontSize': '20px', 'marginRight': '8px'}),
            html.Span("Цвет: Страна", style={'fontSize': '12px'})
        ], style={'marginBottom': '5px'}),
        html.Div([
            html.Span("○", style={'color': 'black', 'fontSize': '20px', 'marginRight': '8px'}),
            html.Span("Размер: Количество случаев", style={'fontSize': '12px'})
        ], style={'marginBottom': '15px'}),
        html.Hr(style={'marginBottom': '10px'})
    ])

    # Создаем скроллируемый контейнер для элементов легенды
    legend_content = html.Div(
        legend_items,
        style={
            'maxHeight': '55vh',
            'overflowY': 'auto',
            'paddingRight': '5px'
        }
    )

    # Объединяем заголовок и содержание легенды
    full_legend = html.Div([legend_header, legend_content])

    return fig, full_legend


# Callback для обновления таблиц (остается без изменений)
@app.callback(
    Output('tables-container', 'children'),
    [Input('country-dropdown', 'value')]
)
def update_tables(selected_country):
    # Загружаем данные для выбранной страны
    country_query = f"SELECT * FROM geo_info.countries WHERE name = '{selected_country}'"
    df = pd.read_sql_query(country_query, engine)

    # Получаем id страны
    country_id = df['id'].iloc[0]

    # Загружаем данные о болезнях
    disease_query = f"""
        SELECT diabetes, obesity, smoking, copd, cvd, hiv, hypertension 
        FROM geo_info.disease_statistics 
        WHERE country_id = {country_id}
    """
    distribution_df = pd.read_sql_query(disease_query, engine)

    # Фильтруем данные о рисках
    country_risk_df = risk_df[risk_df['ID страны'] == country_id]

    # Создаем данные для таблиц
    table_data = [
        {"Параметр": name, "Значение": fmt(df[col].iloc[0])}
        for col, (name, fmt) in config.items()
    ]

    distribution_table_data = [
        {"Параметр": name, "Значение": fmt(distribution_df[col].iloc[0])}
        for col, (name, fmt) in distribution_config.items()
    ]

    risk_table_data = [
        {"Параметр": name, "Значение": fmt(country_risk_df[col].iloc[0])}
        for col, (name, fmt) in risk_config.items()
    ]

    # Создаем таблицы
    tables = html.Div([
        html.Div([
            # Таблица 1 - Общая информация
            html.Div([
                html.Div(
                    "Общая информация",
                    style=header_style
                ),
                dash_table.DataTable(
                    columns=[
                        {"name": "", "id": "Параметр"},
                        {"name": "", "id": "Значение"}
                    ],
                    data=table_data,
                    style_table=table_style,
                    style_cell=cell_style,
                    style_header={'display': 'none'},
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': '#f9f9f9'
                        }
                    ]
                )
            ], style={'flex': '1', 'margin': '5px'}),

            # Таблица 2 - Распространенность болезней
            html.Div([
                html.Div(
                    "Распространенность болезней",
                    style=header_style
                ),
                dash_table.DataTable(
                    columns=[
                        {"name": "", "id": "Параметр"},
                        {"name": "", "id": "Значение"}
                    ],
                    data=distribution_table_data,
                    style_table=table_style,
                    style_cell=cell_style,
                    style_header={'display': 'none'},
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': '#f9f9f9'
                        }
                    ]
                )
            ], style={'flex': '1', 'margin': '5px'}),

            # Таблица 3 - Риски
            html.Div([
                html.Div(
                    "Оценка рисков",
                    style=header_style
                ),
                dash_table.DataTable(
                    columns=[
                        {"name": "", "id": "Параметр"},
                        {"name": "", "id": "Значение"}
                    ],
                    data=risk_table_data,
                    style_table=table_style,
                    style_cell=cell_style,
                    style_header={'display': 'none'},
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': '#f9f9f9'
                        }
                    ]
                )
            ], style={'flex': '1', 'margin': '5px'})
        ], style={
            'display': 'flex',
            'flexWrap': 'nowrap',
            'justifyContent': 'center',
            'overflowX': 'auto'
        })
    ])

    return tables


# Callback для обновления графиков (остается без изменений)
@app.callback(
    Output('graphs-container', 'children'),
    [Input('country-dropdown', 'value')]
)
def update_graphs(selected_country):
    # Фильтруем данные по выбранной стране
    country_daily_data = daily_stats_df[daily_stats_df['name'] == selected_country].copy()

    if country_daily_data.empty:
        return html.Div("Данные по COVID-19 для выбранной страны отсутствуют",
                        style={'textAlign': 'center', 'color': 'red', 'marginTop': '20px'})

    # Сортировка по дате
    country_daily_data['observed_date'] = pd.to_datetime(country_daily_data['observed_date'])
    country_daily_data = country_daily_data.sort_values('observed_date')

    # Проверяем наличие сглаженных столбцов, если нет - используем обычные
    if 'confirmed_per_100k_smoothed' not in country_daily_data.columns:
        country_daily_data['confirmed_per_100k_smoothed'] = country_daily_data['confirmed_per_100k']

    if 'deaths_per_100k_smoothed' not in country_daily_data.columns:
        country_daily_data['deaths_per_100k_smoothed'] = country_daily_data['deaths_per_100k']

    # Создаем графики
    # 1. Гистограмма подтвержденных случаев
    fig_hist_confirmed = go.Figure()
    fig_hist_confirmed.add_trace(go.Histogram(
        x=country_daily_data['confirmed_per_100k'],
        marker_color='blue',
        name='Подтвержденные случаи на 100к'
    ))
    fig_hist_confirmed.update_layout(
        title=f'Распределение подтвержденных случаев в {selected_country}',
        xaxis_title='Случаи на 100 тысяч',
        yaxis_title='Частота',
        template='plotly_white',
        height=400
    )

    # 2. Гистограмма смертей
    fig_hist_deaths = go.Figure()
    fig_hist_deaths.add_trace(go.Histogram(
        x=country_daily_data['deaths_per_100k'],
        marker_color='red',
        name='Смерти на 100к'
    ))
    fig_hist_deaths.update_layout(
        title=f'Распределение смертей в {selected_country}',
        xaxis_title='Смерти на 100 тысяч',
        yaxis_title='Частота',
        template='plotly_white',
        height=400
    )

    # 3. Временной ряд подтвержденных случаев
    fig_ts_confirmed = go.Figure()
    fig_ts_confirmed.add_trace(go.Scatter(
        x=country_daily_data['observed_date'],
        y=country_daily_data['confirmed_per_100k_smoothed'],
        mode='lines',
        line=dict(color='blue', width=2),
        name='Сглаженные случаи'
    ))
    fig_ts_confirmed.update_layout(
        title=f'Динамика подтвержденных случаев в {selected_country}',
        xaxis_title='Дата',
        yaxis_title='Случаи на 100 тысяч',
        template='plotly_white',
        height=400
    )

    # 4. Временной ряд смертей
    fig_ts_deaths = go.Figure()
    fig_ts_deaths.add_trace(go.Scatter(
        x=country_daily_data['observed_date'],
        y=country_daily_data['deaths_per_100k_smoothed'],
        mode='lines',
        line=dict(color='red', width=2),
        name='Сглаженные смерти'
    ))
    fig_ts_deaths.update_layout(
        title=f'Динамика смертей в {selected_country}',
        xaxis_title='Дата',
        yaxis_title='Смерти на 100 тысяч',
        template='plotly_white',
        height=400
    )

    # 5. Boxplot подтвержденных случаев
    fig_box_confirmed = go.Figure()
    fig_box_confirmed.add_trace(go.Box(
        y=country_daily_data['confirmed_per_100k'],
        name='Подтвержденные случаи',
        marker_color='blue',
        boxmean=True
    ))
    fig_box_confirmed.update_layout(
        title=f'Статистика подтвержденных случаев в {selected_country}',
        yaxis_title='Случаи на 100 тысяч',
        template='plotly_white',
        height=400
    )

    # 6. Boxplot смертей
    fig_box_deaths = go.Figure()
    fig_box_deaths.add_trace(go.Box(
        y=country_daily_data['deaths_per_100k'],
        name='Смерти',
        marker_color='red',
        boxmean=True
    ))
    fig_box_deaths.update_layout(
        title=f'Статистика смертей в {selected_country}',
        yaxis_title='Смерти на 100 тысяч',
        template='plotly_white',
        height=400
    )

    # Создаем layout для графиков
    graphs = html.Div([
        # Слой 1: Гистограммы
        html.Div([
            html.H3("Слой 1: Распределение данных (Гистограммы)",
                    style={'textAlign': 'center', 'marginTop': '30px', 'marginBottom': '20px'}),

            html.Div([
                html.Div([
                    dcc.Graph(figure=fig_hist_confirmed)
                ], style={'width': '50%', 'display': 'inline-block', 'padding': '10px'}),

                html.Div([
                    dcc.Graph(figure=fig_hist_deaths)
                ], style={'width': '50%', 'display': 'inline-block', 'padding': '10px'})
            ], style={'display': 'flex'})
        ]),

        # Слой 2: Временные ряды
        html.Div([
            html.H3("Слой 2: Динамика во времени (Временные ряды)",
                    style={'textAlign': 'center', 'marginTop': '30px', 'marginBottom': '20px'}),

            html.Div([
                html.Div([
                    dcc.Graph(figure=fig_ts_confirmed)
                ], style={'width': '50%', 'display': 'inline-block', 'padding': '10px'}),

                html.Div([
                    dcc.Graph(figure=fig_ts_deaths)
                ], style={'width': '50%', 'display': 'inline-block', 'padding': '10px'})
            ], style={'display': 'flex'})
        ]),

        # Слой 3: Ящики с усами
        html.Div([
            html.H3("Слой 3: Статистическое распределение (Ящики с усами)",
                    style={'textAlign': 'center', 'marginTop': '30px', 'marginBottom': '20px'}),

            html.Div([
                html.Div([
                    dcc.Graph(figure=fig_box_confirmed)
                ], style={'width': '50%', 'display': 'inline-block', 'padding': '10px'}),

                html.Div([
                    dcc.Graph(figure=fig_box_deaths)
                ], style={'width': '50%', 'display': 'inline-block', 'padding': '10px'})
            ], style={'display': 'flex'})
        ])
    ])

    return graphs


# Запуск сервера
if __name__ == '__main__':
    app.run(debug=True)