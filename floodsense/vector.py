import rasterio.features
from shapely.geometry import shape
import geopandas as gpd

from datetime import datetime, timezone

def classify_severity(area_ha):
    """
    Classify flood severity based on polygon area.
    Thresholds can be refined later.
    """

    if area_ha < 5:
        return "Low"

    elif area_ha < 50:
        return "Medium"

    else:
        return "High"

def export_mask_to_polygons(
    data_array,
    output_filename="flood_polygons.geojson",
    event_date=None,
    event_datetime=None,
    scene_id=None,
    orbit_state=None,
    source="FloodSense Sentinel-1 SAR",
    baseline_scene_id=None,
    threshold_db=None,
    smoothing_window=None,
    processing_version="0.0.1",
    change_vv=None,
    change_vh=None
):
    """
    Converts a binary xarray DataArray mask into a GeoDataFrame of polygons,
    keeping only the areas where the value is 1, and exports it.
    """
    print("Vectorizing raster mask to polygons...")
    
    # Ensure the data is in the correct integer format for rasterio
    # Fill any NaNs with 0 before converting
    mask_data = data_array.fillna(0).values.astype('uint8')
    
    # Get the spatial transform to convert pixel coordinates to real-world coordinates
    transform = data_array.rio.transform()
    
    # Extract shapes. The 'mask' parameter ensures we ONLY process pixels where value == 1
    shapes_generator = rasterio.features.shapes(
        mask_data,
        mask=(mask_data == 1),
        transform=transform
    )
    
    # Convert the extracted rasterio shapes into Shapely geometries
    geometries = [shape(geom) for geom, value in shapes_generator]
    
    if len(geometries) == 0:
        print("Warning: No pixels with value 1 found. No polygons generated.")
        return None
        
    # Create a GeoDataFrame using the geometries and the original CRS
    gdf = gpd.GeoDataFrame(
        {
            "flood_id": range(1, len(geometries) + 1)
        },
        geometry=geometries,
        crs=data_array.rio.crs
    )

    # Event metadata
    gdf["event_date"] = event_date
    gdf["event_datetime"] = event_datetime
    gdf["scene_id"] = scene_id
    gdf["orbit_state"] = orbit_state

    # Processing metadata
    gdf["baseline_scene_id"] = baseline_scene_id
    gdf["threshold_db"] = threshold_db
    gdf["smoothing_window"] = smoothing_window
    gdf["processing_version"] = processing_version

    # Operational metadata
    gdf["source"] = source
    gdf["status"] = "Potential Flooding"
    gdf["processed_utc"] = datetime.now(
        timezone.utc
    ).isoformat()

    # Area metrics
    gdf["area_m2"] = gdf.geometry.area
    gdf["area_ha"] = gdf["area_m2"] / 10000
    gdf["area_km2"] = gdf["area_m2"] / 1000000

    # Severity classification
    gdf["severity"] = gdf["area_ha"].apply(
        classify_severity
    )

    gdf["mean_vv_change_db"] = None
    gdf["mean_vh_change_db"] = None

    gdf["max_vv_change_db"] = None
    gdf["max_vh_change_db"] = None
    
    # Export to file (GeoJSON or Shapefile depending on the extension provided)
    try:
        gdf.to_file(output_filename)
        print(f"Successfully exported {len(gdf)} polygons to: {output_filename}")
    except Exception as e:
        print(f"Vector export failed: {e}")
        
    return gdf