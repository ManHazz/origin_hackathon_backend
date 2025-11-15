from utils.normalize import normalize_scores
import random
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOPOJSON_PATH = os.path.join(BASE_DIR, "..", "countries.json")
TOPOJSON_PATH = os.path.abspath(TOPOJSON_PATH)

print("Loading countries from:", TOPOJSON_PATH)

with open(TOPOJSON_PATH, "r", encoding="utf-8") as f:
    topo = json.load(f)

# Extract countries from TopoJSON
geometries = topo["objects"]["countries"]["geometries"]

COUNTRY_NAMES = [
    geom["properties"]["name"]
    for geom in geometries
    if "name" in geom["properties"]
]

def get_country_search_density(keyword: str):
    random.seed(keyword)  # same keyword -> same scores
    result = [{"country": name, "score": random.randint(0, 100)} for name in COUNTRY_NAMES]
    return normalize_scores(result)
