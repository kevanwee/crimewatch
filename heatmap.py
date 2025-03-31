import pandas as pd
import folium
from folium.plugins import HeatMap

def create_crime_heatmap(file_name):
    if file_name.endswith('.csv'):
        df = pd.read_csv(file_name)
    elif file_name.endswith('.xlsx'):
        df = pd.read_excel(file_name)
    else:
        raise ValueError("Invalid file type. Please provide a CSV or XLSX file.")

    if not {'Latitude', 'Longitude', 'CrimeType'}.issubset(df.columns):
        raise ValueError("CSV/XLSX must contain 'Latitude', 'Longitude', and 'CrimeType' columns")

    # center to sg coord in wgs 84 (epsg 4326)
    m = folium.Map(location=[1.3521, 103.8198], zoom_start=12)

    heat_data = df[['Latitude', 'Longitude']].dropna().values.tolist()
    HeatMap(heat_data).add_to(m)
  
    map_filename = "crime_heatmap.html"
    m.save(map_filename)
    print(f"Heatmap saved as {map_filename}")

    return map_filename

