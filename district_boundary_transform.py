import requests
import zipfile
import io
import json
from shapely.geometry import shape, mapping
from pyproj import Transformer

# Define the transformation parameters
epsgTransformer = Transformer.from_crs('epsg:2326', 'epsg:4326', always_xy=True)

# Step 1: Download the ZIP file
url = "https://static.csdi.gov.hk/csdi-webpage/download/0dc7f67554fc5d14a185fb1ee36494c2/geojson"
response = requests.get(url)
response.raise_for_status()
zip_file = zipfile.ZipFile(io.BytesIO(response.content))

# Step 2: Extract the GeoJSON file
geojson_filename = next((name for name in zip_file.namelist() if name.endswith('.json')), None)
if not geojson_filename:
    raise FileNotFoundError("No GeoJSON file found in the downloaded ZIP.")
with zip_file.open(geojson_filename) as file:
    geojson_data = json.load(file)

# Step 3: Transform and process features
def transform_coordinates(geometry):
    if geometry['type'] == 'Point':
        geometry['coordinates'] = list(epsgTransformer.transform(*geometry['coordinates']))
    elif geometry['type'] in ['LineString', 'MultiPoint']:
        geometry['coordinates'] = [list(epsgTransformer.transform(*coord)) for coord in geometry['coordinates']]
    elif geometry['type'] in ['Polygon', 'MultiLineString']:
        geometry['coordinates'] = [[list(epsgTransformer.transform(*coord)) for coord in ring] for ring in geometry['coordinates']]
    elif geometry['type'] == 'MultiPolygon':
        geometry['coordinates'] = [[[list(epsgTransformer.transform(*coord)) for coord in ring] for ring in polygon] for polygon in geometry['coordinates']]
    return geometry

def simplify_geometry(geometry, max_resolution=0.00001):
    shapely_geom = shape(geometry)
    simplified_geom = shapely_geom.simplify(max_resolution, preserve_topology=True)
    return mapping(simplified_geom)

def expand_geometry(geometry, max_resolution=0.00001 * 2):
    shapely_geom = shape(geometry)
    expanded_geom = shapely_geom.buffer(max_resolution)
    return mapping(expanded_geom)

def round_coordinates(geometry):
    if geometry['type'] == 'Point':
        geometry['coordinates'] = [round(coord, 5) for coord in geometry['coordinates']]
    elif geometry['type'] in ['LineString', 'MultiPoint']:
        geometry['coordinates'] = [[round(coord, 5) for coord in pair] for pair in geometry['coordinates']]
    elif geometry['type'] in ['Polygon', 'MultiLineString']:
        geometry['coordinates'] = [[[round(coord, 5) for coord in pair] for pair in ring] for ring in geometry['coordinates']]
    elif geometry['type'] == 'MultiPolygon':
        geometry['coordinates'] = [[[[round(coord, 5) for coord in pair] for pair in ring] for ring in polygon] for polygon in geometry['coordinates']]
    return geometry

for feature in geojson_data['features']:
    feature['geometry'] = transform_coordinates(feature['geometry'])
    feature['geometry'] = simplify_geometry(feature['geometry'])
    feature['geometry'] = expand_geometry(feature['geometry'])  # Expand the polygon
    feature['geometry'] = round_coordinates(feature['geometry'])

# Step 4: Save the final GeoJSON
output_filename = "district_boundaries.geojson"
with open(output_filename, 'w', encoding='utf-8') as file:
    json.dump(geojson_data, file, ensure_ascii=False, separators=(',', ':'))

print(f"GeoJSON file saved as {output_filename}")
