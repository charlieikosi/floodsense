import geopandas as gpd
import pystac_client
import planetary_computer


from datetime import datetime
import pytz

def get_rtc_catalog_items(shapefile_path, date_range):
    """
    Finds Sentinel-1 RTC items and handles CRS projection for the search.
    """
    # 1. Load AOI and reproject to WGS84 (EPSG:4326) for STAC search
    aoi = gpd.read_file(shapefile_path)
    aoi_wgs84 = aoi.to_crs("EPSG:4326")
    
    # Use bounding box (minx, miny, maxx, maxy) for API stability
    bounds = list(aoi_wgs84.total_bounds)

    # 2. Open the catalog with the required signing modifier
    catalog = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace
    )

    # 3. Perform the search with explicit limits to prevent timeouts
    search = catalog.search(
        collections=["sentinel-1-rtc"],
        bbox=bounds,
        datetime=date_range,
        limit=50  # Smaller page size is easier for the API to process 
    )

    try:
        # Fetch the item collection [cite: 540, 702]
        items = search.item_collection()
        
        if len(items) == 0:
            print(f"No items found for {date_range}. Check your AOI and dates.")
            return None, aoi_wgs84
            
        print(f"Successfully found {len(items)} items.")
        return items, aoi_wgs84
        
    except Exception as e:
        print(f"STAC API Error: {e}")
        return None, None
    

def select_scenes_by_orbit(items, orbit_state="descending"):
    """
    Filters a list of STAC items to only include a specific orbit state.
    Consistent orbit direction is critical to avoid geometric artifacts 
    in SAR change detection.
    """
    if items is None:
        return []

    # Filter items based on the 'sat:orbit_state' property 
    selected_items = [
        item for item in items 
        if item.properties.get("sat:orbit_state") == orbit_state
    ]

    print(f"Filtered to {len(selected_items)} {orbit_state} scenes.")
    
    if len(selected_items) == 0:
        print(f"Warning: No scenes found for orbit: {orbit_state}. "
              "Check available metadata or try 'ascending'.")
        
    return selected_items

def select_scene_for_processing(items, index=0):
    """
    Selects a single STAC item and prints metadata in NZ timezone.
    """
    if not items:
        print("No items available to select.")
        return None

    # Sort items by datetime (most recent first)
    sorted_items = sorted(
        items, 
        key=lambda x: x.datetime, 
        reverse=True
    )

    selected_item = sorted_items[index]
    
    # 1. Get the UTC datetime from the item
    utc_dt = selected_item.datetime
    
    # 2. Convert to New Zealand Timezone
    nz_tz = pytz.timezone("Pacific/Auckland")
    nz_dt = utc_dt.astimezone(nz_tz)
    
    # 3. Format for readable output
    nz_format = nz_dt.strftime("%d-%m-%Y %H:%M:%S")

    print(f"Selected Scene ID: {selected_item.id}")
    print(f"Acquisition Date (NZT): {nz_format}")
    
    return selected_item