import streamlit as st
import pandas as pd
import requests
import folium
from folium.plugins import HeatMap
from streamlit_folium import folium_static
import datetime
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go

# Configuración de la página
st.set_page_config(
    page_title="Análisis de Sequía en México",
    page_icon="🌧️",
    layout="wide"
)

# API Key fija - Reemplaza esto con tu propia API key
API_KEY = st.secrets["OPENWEATHER_API_KEY"]

# Título y descripción
st.title("Análisis de Sequía en México")
st.markdown("""
Esta aplicación muestra la probabilidad de lluvia en los próximos días para diferentes estados de México.
Los datos son obtenidos en tiempo real desde la API de OpenWeather.
""")

# Función para obtener datos climáticos actuales de OpenWeather
@st.cache_data(ttl=3600, show_spinner="Cargando datos actuales...")
def get_current_weather(lat, lon, api_key):
    """Obtiene datos actuales de clima usando la API gratuita"""
    
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=es"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error al obtener datos actuales: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Error en la solicitud: {e}")
        return None

# Función para obtener pronóstico de 5 días
@st.cache_data(ttl=3600, show_spinner="Cargando pronóstico...")
def get_forecast(lat, lon, api_key):
    """Obtiene pronóstico de 5 días usando la API gratuita"""
    
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=es"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error al obtener pronóstico: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Error en la solicitud: {e}")
        return None

# Función para analizar si hay lluvia en el pronóstico
def analyze_rain_forecast(forecast_data):
    """Analiza si hay lluvia en el pronóstico de 5 días y calcula la probabilidad"""
    
    if not forecast_data or 'list' not in forecast_data:
        return {
            "lluvia_proximos_dias": False,
            "probabilidad_lluvia": 0,
            "dias_con_lluvia": 0,
            "proxima_lluvia": None,
            "datos_diarios": []
        }
    
    rain_days = 0
    first_rain = None
    total_periods = len(forecast_data['list'])
    rain_periods = 0
    
    # Umbral para considerar lluvia (en mm)
    threshold = 1.0
    
    # Diccionario para almacenar datos diarios
    daily_data = {}
    
    # Analizar cada período del pronóstico (cada 3 horas durante 5 días)
    for period in forecast_data['list']:
        # Verificar si hay lluvia en este período
        rain_amount = 0
        if 'rain' in period and '3h' in period['rain']:
            rain_amount = period['rain']['3h']
        
        # Obtener fecha y temperatura
        timestamp = period['dt']
        date_time = datetime.fromtimestamp(timestamp)
        date_str = date_time.strftime('%Y-%m-%d')
        temp = period['main']['temp']
        
        # Si hay lluvia significativa
        if rain_amount >= threshold:
            rain_periods += 1
            
            # Si es el primer período con lluvia, guardar la fecha
            if first_rain is None:
                first_rain = date_time
        
        # Agregar o actualizar datos diarios
        if date_str not in daily_data:
            daily_data[date_str] = {
                'fecha': date_time.date(),
                'min_temp': temp,
                'max_temp': temp,
                'precipitacion': rain_amount,
                'tiene_lluvia': rain_amount >= threshold
            }
        else:
            daily_data[date_str]['min_temp'] = min(daily_data[date_str]['min_temp'], temp)
            daily_data[date_str]['max_temp'] = max(daily_data[date_str]['max_temp'], temp)
            daily_data[date_str]['precipitacion'] += rain_amount
            daily_data[date_str]['tiene_lluvia'] = daily_data[date_str]['tiene_lluvia'] or (rain_amount >= threshold)
    
    # Contar días únicos con lluvia
    for day_data in daily_data.values():
        if day_data['tiene_lluvia']:
            rain_days += 1
    
    # Convertir diccionario a lista
    daily_data_list = list(daily_data.values())
    
    # Calcular probabilidad de lluvia
    rain_probability = (rain_periods / total_periods) * 100 if total_periods > 0 else 0
    
    return {
        "lluvia_proximos_dias": rain_periods > 0,
        "probabilidad_lluvia": round(rain_probability, 1),
        "dias_con_lluvia": rain_days,
        "proxima_lluvia": first_rain,
        "datos_diarios": daily_data_list
    }

# Datos de los estados de México (nombre, latitud, longitud)
estados_mexico = [
    {"nombre": "Aguascalientes", "lat": 21.8818, "lon": -102.2916, "region": "Centro"},
    {"nombre": "Baja California", "lat": 30.8406, "lon": -115.2838, "region": "Norte"},
    {"nombre": "Baja California Sur", "lat": 26.0444, "lon": -111.6661, "region": "Norte"},
    {"nombre": "Campeche", "lat": 19.8301, "lon": -90.5349, "region": "Sur"},
    {"nombre": "Chiapas", "lat": 16.7569, "lon": -93.1292, "region": "Sur"},
    {"nombre": "Chihuahua", "lat": 28.6353, "lon": -106.0889, "region": "Norte"},
    {"nombre": "Ciudad de México", "lat": 19.4326, "lon": -99.1332, "region": "Centro"},
    {"nombre": "Coahuila", "lat": 27.0587, "lon": -101.7068, "region": "Norte"},
    {"nombre": "Colima", "lat": 19.2452, "lon": -103.7241, "region": "Centro"},
    {"nombre": "Durango", "lat": 24.0277, "lon": -104.6532, "region": "Norte"},
    {"nombre": "Estado de México", "lat": 19.4969, "lon": -99.7233, "region": "Centro"},
    {"nombre": "Guanajuato", "lat": 20.9170, "lon": -101.1617, "region": "Centro"},
    {"nombre": "Guerrero", "lat": 17.4392, "lon": -99.5451, "region": "Sur"},
    {"nombre": "Hidalgo", "lat": 20.0911, "lon": -98.7624, "region": "Centro"},
    {"nombre": "Jalisco", "lat": 20.6595, "lon": -103.3494, "region": "Centro"},
    {"nombre": "Michoacán", "lat": 19.5665, "lon": -101.7068, "region": "Centro"},
    {"nombre": "Morelos", "lat": 18.6813, "lon": -99.1013, "region": "Centro"},
    {"nombre": "Nayarit", "lat": 21.7514, "lon": -104.8455, "region": "Centro"},
    {"nombre": "Nuevo León", "lat": 25.5922, "lon": -99.9962, "region": "Norte"},
    {"nombre": "Oaxaca", "lat": 17.0732, "lon": -96.7266, "region": "Sur"},
    {"nombre": "Puebla", "lat": 19.0414, "lon": -98.2063, "region": "Centro"},
    {"nombre": "Querétaro", "lat": 20.5888, "lon": -100.3899, "region": "Centro"},
    {"nombre": "Quintana Roo", "lat": 19.1817, "lon": -88.4791, "region": "Sur"},
    {"nombre": "San Luis Potosí", "lat": 22.1565, "lon": -100.9855, "region": "Centro"},
    {"nombre": "Sinaloa", "lat": 25.1721, "lon": -107.4795, "region": "Norte"},
    {"nombre": "Sonora", "lat": 29.2970, "lon": -110.3309, "region": "Norte"},
    {"nombre": "Tabasco", "lat": 17.8409, "lon": -92.6189, "region": "Sur"},
    {"nombre": "Tamaulipas", "lat": 24.2669, "lon": -98.8363, "region": "Norte"},
    {"nombre": "Tlaxcala", "lat": 19.3139, "lon": -98.2404, "region": "Centro"},
    {"nombre": "Veracruz", "lat": 19.1738, "lon": -96.1342, "region": "Sur"},
    {"nombre": "Yucatán", "lat": 20.7099, "lon": -89.0943, "region": "Sur"},
    {"nombre": "Zacatecas", "lat": 22.7709, "lon": -102.5832, "region": "Centro"}
]

# Sidebar para controles
st.sidebar.title("Configuración")

# Selector para mostrar todos los estados o solo una región
region_options = ["Todos los estados", "Norte", "Centro", "Sur"]
selected_region = st.sidebar.selectbox("Región a mostrar", region_options)

# Filtrar estados según la región seleccionada
if selected_region == "Norte":
    estados_filtrados = [estado for estado in estados_mexico if estado["region"] == "Norte"]
elif selected_region == "Centro":
    estados_filtrados = [estado for estado in estados_mexico if estado["region"] == "Centro"]
elif selected_region == "Sur":
    estados_filtrados = [estado for estado in estados_mexico if estado["region"] == "Sur"]
else:
    estados_filtrados = estados_mexico

# Manejo de estado de la sesión
if 'last_update' not in st.session_state:
    st.session_state.last_update = None

if 'results_data' not in st.session_state:
    st.session_state.results_data = None

# Botón para actualizar datos
update_button = st.sidebar.button("Actualizar datos")

# Cargar datos iniciales o actualizar según el botón
if update_button or st.session_state.results_data is None:
    with st.spinner('Cargando datos climáticos...'):
            # Barra de progreso
            progress_bar = st.progress(0)
            
            results = []
            datos_diarios_por_estado = {}
            
            for i, estado in enumerate(estados_filtrados):
                # Actualizar barra de progreso
                progress_bar.progress((i + 1) / len(estados_filtrados))
                
                # Obtener datos actuales
                current_data = get_current_weather(estado["lat"], estado["lon"], API_KEY)
                
                # Obtener pronóstico
                forecast_data = get_forecast(estado["lat"], estado["lon"], API_KEY)
                
                # Analizar si hay lluvia en el pronóstico
                rain_analysis = analyze_rain_forecast(forecast_data)
                
                # Guardar datos diarios por estado
                datos_diarios_por_estado[estado["nombre"]] = rain_analysis["datos_diarios"]
                
                # Obtener información actual
                temp_actual = None
                clima_actual = None
                humedad_actual = None
                presion_actual = None
                viento_actual = None
                icon_code = None
                
                if current_data and 'main' in current_data:
                    temp_actual = current_data['main'].get('temp')
                    humedad_actual = current_data['main'].get('humidity')
                    presion_actual = current_data['main'].get('pressure')
                    
                    if 'wind' in current_data:
                        viento_actual = current_data['wind'].get('speed')
                    
                    if 'weather' in current_data and len(current_data['weather']) > 0:
                        clima_actual = current_data['weather'][0].get('description')
                        icon_code = current_data['weather'][0].get('icon')
                
                # Guardar resultados
                results.append({
                    "nombre": estado["nombre"],
                    "region": estado["region"],
                    "lat": estado["lat"],
                    "lon": estado["lon"],
                    "temp_actual": temp_actual,
                    "clima_actual": clima_actual,
                    "humedad_actual": humedad_actual,
                    "presion_actual": presion_actual,
                    "viento_actual": viento_actual,
                    "icon_code": icon_code,
                    "lluvia_proximos_dias": rain_analysis["lluvia_proximos_dias"],
                    "probabilidad_lluvia": rain_analysis["probabilidad_lluvia"],
                    "dias_con_lluvia": rain_analysis["dias_con_lluvia"],
                    "proxima_lluvia": rain_analysis["proxima_lluvia"]
                })
            
            # Guardar datos en session_state
            st.session_state.results_data = results
            st.session_state.datos_diarios_por_estado = datos_diarios_por_estado
            
            # Limpiar barra de progreso
            progress_bar.empty()

# Usar los datos almacenados en session_state
if st.session_state.results_data:
    # Convertir a DataFrame
    df_estados = pd.DataFrame(st.session_state.results_data)
    
    # Crear mapa
    m = folium.Map(location=[23.6345, -102.5528], zoom_start=5)
    
    # Añadir marcadores para cada estado
    for _, row in df_estados.iterrows():
        # Determinar color basado en probabilidad de lluvia
        if row["probabilidad_lluvia"] > 50:
            color = "green"
        elif row["probabilidad_lluvia"] > 30:
            color = "lightblue"
        elif row["probabilidad_lluvia"] > 10:
            color = "orange"
        else:
            color = "red"
            
        # Crear popup con información
        popup_html = f"""
        <div style="width: 200px">
            <h4>{row['nombre']}</h4>
            <p><b>Temperatura actual:</b> {row['temp_actual']}°C</p>
            <p><b>Clima actual:</b> {row['clima_actual']}</p>
            <p><b>Humedad:</b> {row['humedad_actual']}%</p>
            <p><b>Viento:</b> {row['viento_actual']} m/s</p>
            <p><b>Probabilidad de lluvia (5 días):</b> {row['probabilidad_lluvia']}%</p>
            <p><b>Días con lluvia prevista:</b> {row['dias_con_lluvia']}</p>
            <p><b>Próxima lluvia:</b> {row['proxima_lluvia'].strftime('%d/%m/%Y %H:%M') if not pd.isnull(row['proxima_lluvia']) else 'No prevista'}</p>
        </div>
        """
        
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=10,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            popup=folium.Popup(popup_html, max_width=300)
        ).add_to(m)
    
    # Añadir leyenda
    legend_html = '''
    <div style="position: fixed; 
        bottom: 50px; left: 50px; width: 250px; height: 130px; 
        border:2px solid grey; z-index:9999; font-size:14px;
        background-color:white;
        padding: 10px;
        border-radius: 5px;
        ">
        <p><i class="fa fa-circle" style="color:green"></i> Probabilidad alta (>50%)</p>
        <p><i class="fa fa-circle" style="color:lightblue"></i> Probabilidad media (30-50%)</p>
        <p><i class="fa fa-circle" style="color:orange"></i> Probabilidad baja (10-30%)</p>
        <p><i class="fa fa-circle" style="color:red"></i> Sin lluvia prevista (<10%)</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Mostrar mapa en Streamlit
    st.subheader("Mapa de probabilidad de lluvia por estado")
    folium_static(m)
    
    # Mostrar pestañas con diferentes visualizaciones
    tab1, tab2, tab3, tab4 = st.tabs(["Datos actuales", "Pronóstico de lluvia", "Análisis regional", "Tendencias"])
    
    with tab1:
        # Mostrar datos actuales en una tabla
        st.subheader("Condiciones actuales por estado")
        
        # Crear columnas para mostrar tarjetas de estados
        col1, col2 = st.columns(2)
        
        # Ordenar estados por temperatura (de mayor a menor)
        df_temp = df_estados.sort_values(by="temp_actual", ascending=False)
        
        with col1:
            st.markdown("#### Estados más calurosos")
            for _, row in df_temp.head(5).iterrows():
                with st.container():
                    st.markdown(f"""
                    <div style="border:1px solid #ddd; border-radius:5px; padding:10px; margin-bottom:10px;">
                        <h5>{row['nombre']} - {row['temp_actual']}°C</h5>
                        <p>{row['clima_actual']}</p>
                        <p>Humedad: {row['humedad_actual']}% | Viento: {row['viento_actual']} m/s</p>
                    </div>
                    """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("#### Estados más frescos")
            for _, row in df_temp.tail(5).iterrows():
                with st.container():
                    st.markdown(f"""
                    <div style="border:1px solid #ddd; border-radius:5px; padding:10px; margin-bottom:10px;">
                        <h5>{row['nombre']} - {row['temp_actual']}°C</h5>
                        <p>{row['clima_actual']}</p>
                        <p>Humedad: {row['humedad_actual']}% | Viento: {row['viento_actual']} m/s</p>
                    </div>
                    """, unsafe_allow_html=True)
        
        # Mostrar todos los datos en una tabla
        st.markdown("#### Datos de todos los estados")
        st.dataframe(
            df_estados[["nombre", "region", "temp_actual", "clima_actual", "humedad_actual", "viento_actual"]]
            .rename(columns={
                "nombre": "Estado", 
                "region": "Región",
                "temp_actual": "Temperatura (°C)", 
                "clima_actual": "Clima", 
                "humedad_actual": "Humedad (%)", 
                "viento_actual": "Viento (m/s)"
            })
            .sort_values(by="Estado")
        )
    
    with tab2:
        # Mostrar pronóstico en una tabla
        st.subheader("Pronóstico de lluvia para los próximos 5 días")
        
        # Crear una columna formateada para mostrar la próxima lluvia
        df_pronostico = df_estados.copy()
        df_pronostico["proxima_lluvia_fmt"] = df_pronostico["proxima_lluvia"].apply(
            lambda x: x.strftime("%d/%m/%Y %H:%M") if not pd.isnull(x) else "No prevista"
        )
        
        # Crear gráfico de mapa de calor para probabilidad de lluvia
        fig = px.choropleth(
            df_pronostico,
            locations="nombre",
            color="probabilidad_lluvia",
            hover_name="nombre",
            color_continuous_scale="Blues",
            labels={"probabilidad_lluvia": "Probabilidad de lluvia (%)"},
            title="Mapa de calor de probabilidad de lluvia por estado"
        )
        
        # Intentar ajustar el mapa a México, pero como usamos nombres en lugar de códigos geográficos, esto es limitado
        fig.update_geos(
            visible=False,
            showcountries=True,
            showcoastlines=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Mostrar tabla de pronóstico
        st.dataframe(
            df_pronostico[["nombre", "region", "probabilidad_lluvia", "dias_con_lluvia", "proxima_lluvia_fmt"]]
            .rename(columns={
                "nombre": "Estado", 
                "region": "Región",
                "probabilidad_lluvia": "Prob. lluvia (%)", 
                "dias_con_lluvia": "Días con lluvia", 
                "proxima_lluvia_fmt": "Próxima lluvia"
            })
            .sort_values(by="Prob. lluvia (%)", ascending=False)
        )
        
        # Mostrar detalles de pronóstico diario para un estado seleccionado
        st.subheader("Pronóstico diario detallado")
        
        # Selector de estado
        estado_seleccionado = st.selectbox(
            "Selecciona un estado para ver el pronóstico diario detallado",
            df_estados["nombre"].tolist()
        )
        
        if estado_seleccionado and estado_seleccionado in st.session_state.datos_diarios_por_estado:
            datos_diarios = st.session_state.datos_diarios_por_estado[estado_seleccionado]
            if datos_diarios:
                # Convertir a DataFrame
                df_diario = pd.DataFrame(datos_diarios)
                
                # Formatear fecha
                df_diario["fecha_str"] = df_diario["fecha"].apply(lambda x: x.strftime("%d/%m/%Y"))
                
                # Crear gráfico de temperatura máxima y mínima
                fig_temp = go.Figure()
                
                fig_temp.add_trace(
                    go.Scatter(
                        x=df_diario["fecha_str"],
                        y=df_diario["max_temp"],
                        mode="lines+markers",
                        name="Temp. Máxima",
                        line=dict(color="red")
                    )
                )
                
                fig_temp.add_trace(
                    go.Scatter(
                        x=df_diario["fecha_str"],
                        y=df_diario["min_temp"],
                        mode="lines+markers",
                        name="Temp. Mínima",
                        line=dict(color="blue")
                    )
                )
                
                fig_temp.update_layout(
                    title=f"Pronóstico de temperatura para {estado_seleccionado}",
                    xaxis_title="Fecha",
                    yaxis_title="Temperatura (°C)",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                
                st.plotly_chart(fig_temp, use_container_width=True)
                
                # Crear gráfico de precipitación
                fig_precip = go.Figure()
                
                fig_precip.add_trace(
                    go.Bar(
                        x=df_diario["fecha_str"],
                        y=df_diario["precipitacion"],
                        name="Precipitación",
                        marker_color="skyblue"
                    )
                )
                
                fig_precip.update_layout(
                    title=f"Pronóstico de precipitación para {estado_seleccionado}",
                    xaxis_title="Fecha",
                    yaxis_title="Precipitación (mm)",
                    showlegend=False
                )
                
                st.plotly_chart(fig_precip, use_container_width=True)
            else:
                st.write("No hay datos diarios disponibles para este estado")
    
    with tab3:
        # Análisis regional
        st.subheader("Análisis regional de probabilidad de lluvia")
        
        # Agrupar por región
        df_regional = df_estados.groupby("region").agg({
            "probabilidad_lluvia": "mean",
            "dias_con_lluvia": "mean",
            "nombre": "count"
        }).reset_index()
        
        df_regional = df_regional.rename(columns={
            "probabilidad_lluvia": "Prob. lluvia promedio (%)",
            "dias_con_lluvia": "Días con lluvia promedio",
            "nombre": "Número de estados"
        })
        
        # Mostrar tabla regional
        st.dataframe(df_regional)
        
        # Crear gráfico de barras para probabilidad de lluvia por región
        fig_region = px.bar(
            df_regional,
            x="region",
            y="Prob. lluvia promedio (%)",
            text="Prob. lluvia promedio (%)",
            color="region",
            labels={"region": "Región"},
            title="Probabilidad de lluvia promedio por región"
        )
        
        fig_region.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        
        st.plotly_chart(fig_region, use_container_width=True)
        
        # Gráfico de días con lluvia por región
        fig_dias = px.bar(
            df_regional,
            x="region",
            y="Días con lluvia promedio",
            text="Días con lluvia promedio",
            color="region",
            labels={"region": "Región"},
            title="Días con lluvia promedio por región"
        )
        
        fig_dias.update_traces(texttemplate='%{text:.1f}', textposition='outside')
        
        st.plotly_chart(fig_dias, use_container_width=True)
    
    with tab4:
        # Análisis de tendencias y correlaciones
        st.subheader("Análisis de tendencias y correlaciones")
        
        # Crear gráfico de dispersión entre temperatura y humedad
        fig_scatter = px.scatter(
            df_estados,
            x="temp_actual",
            y="humedad_actual",
            size="probabilidad_lluvia",
            color="region",
            hover_name="nombre",
            labels={
                "temp_actual": "Temperatura (°C)",
                "humedad_actual": "Humedad (%)",
                "probabilidad_lluvia": "Prob. de lluvia (%)",
                "region": "Región"
            },
            title="Correlación entre temperatura, humedad y probabilidad de lluvia"
        )
        
        st.plotly_chart(fig_scatter, use_container_width=True)
        
        # Calcular correlaciones
        corr_cols = ["temp_actual", "humedad_actual", "presion_actual", "viento_actual", "probabilidad_lluvia", "dias_con_lluvia"]
        df_corr = df_estados[corr_cols].corr()
        
        # Visualizar matriz de correlación
        fig_corr = px.imshow(
            df_corr,
            text_auto=True,
            color_continuous_scale="RdBu_r",
            title="Matriz de correlación entre variables climáticas"
        )
        
        st.plotly_chart(fig_corr, use_container_width=True)
        
        # Análisis de distribución de probabilidad de lluvia
        st.subheader("Distribución de probabilidad de lluvia")
        
        fig_hist = px.histogram(
            df_estados,
            x="probabilidad_lluvia",
            nbins=20,
            color="region",
            labels={"probabilidad_lluvia": "Probabilidad de lluvia (%)"},
            title="Distribución de probabilidad de lluvia por región"
        )
        
        st.plotly_chart(fig_hist, use_container_width=True)
        
        # Calcular estadísticas descriptivas
        st.subheader("Estadísticas climáticas descriptivas")
        
        df_stats = df_estados[["temp_actual", "humedad_actual", "probabilidad_lluvia"]].describe().reset_index()
        df_stats = df_stats.rename(columns={
            "index": "Estadística",
            "temp_actual": "Temperatura (°C)",
            "humedad_actual": "Humedad (%)",
            "probabilidad_lluvia": "Prob. lluvia (%)"
        })
        
        st.dataframe(df_stats)

# Información adicional COMPLETADA
st.sidebar.markdown("---")
st.sidebar.markdown("""
## Información del proyecto
Este proyecto visualiza datos climáticos de México obtenidos de OpenWeather, centrándose en el análisis de probabilidad de lluvia y condiciones de sequía.

### Metodología
- **Fuente de Datos:** Datos en tiempo real de OpenWeather API (pronóstico de 5 días)
- **Definición de Lluvia:** Se considera lluvia significativa cuando se registra más de 1mm de precipitación en 3 horas
- **Cálculo de Probabilidad:** Porcentaje de períodos de 3 horas con lluvia en los próximos 5 días
- **Regiones:** 
  - Norte: Estados fronterizos y zonas áridas
  - Centro: Zona del altiplano central
  - Sur: Estados con clima tropical húmedo

### Limitaciones
- Los datos se basan en coordenadas centrales de cada estado
- La API gratuita tiene una precisión limitada (pronóstico cada 3 horas)
- No considera microclimas o variaciones locales

### Tecnologías Utilizadas
- Python 3.11
- Streamlit para la interfaz web
- OpenWeather API para datos climáticos
- Folium y Plotly para visualizaciones
- Pandas para análisis de datos

### Autor
[Jorge SHK] - Proyecto para portafolio de Data Analyst

✉️ Contacto: [jorgesherrerak@gmail.com](mailto:tu_email@dominio.com)

🔗 [LinkedIn](https://www.linkedin.com/in/jorge-shk/)
""")

# Sección de metodología en el main
st.markdown("---")
st.markdown("""
### Detalles Técnicos
1. **Actualización de Datos:** 
   - Los datos se actualizan automáticamente cada 1 hora
   - Última actualización: {}
   
2. **Código Fuente:** 
   [Repositorio en GitHub](https://github.com/tuusuario/sequia-mexico)

3. **Licencia:** 
   MIT License - Uso libre para fines educativos
""".format(st.session_state.last_update.strftime('%d/%m/%Y %H:%M') if st.session_state.last_update else "N/A"))

with st.expander("📚 Guía Rápida - Cómo Funciona Esta App"):
    st.markdown("""
    ## 🎯 Objetivo
    Analizar patrones de sequía mediante:
    - Mapa interactivo de probabilidad de lluvia
    - Pronóstico de temperatura y precipitación

    ## 🔧 Mecánica Técnica
    ```python
    # Paso 1: Obtener datos
    response = requests.get(api_url)
    
    # Paso 2: Calcular métricas
    probabilidad = (periodos_lluvia / total_periodos) * 100
    
    # Paso 3: Visualizar
    folium.Map().add_child(HeatMap(data))
    ```
    
    ## 📊 Interpretación de Gráficos
    | Gráfico | Elemento Clave | Insight |
    |---------|----------------|---------|
    | Matriz Correlación | Valores cerca de +1/-1 | Relaciones fuertes positivas/negativas |
    """)
