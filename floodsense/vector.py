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


def classify_confidence(
    area_ha,
    mean_vv_change_db,
    mean_vh_change_db
):
    """
    Calculate a confidence score (0-100)
    using VV change, VH change and flood area.
    """

    score = 0

    # VH component (0-50)
    if mean_vh_change_db <= -5:
        score += 50

    elif mean_vh_change_db <= -4:
        score += 35

    elif mean_vh_change_db <= -3:
        score += 20

    # VV component (0-30)
    if mean_vv_change_db <= -3:
        score += 30

    elif mean_vv_change_db <= -2:
        score += 20

    elif mean_vv_change_db <= -1:
        score += 10

    # Area component (0-20)
    if area_ha >= 50:
        score += 20

    elif area_ha >= 5:
        score += 10

    else:
        score += 5

    # Classification
    if score >= 85:
        confidence = "Very High"

    elif score >= 65:
        confidence = "High"

    elif score >= 40:
        confidence = "Medium"

    else:
        confidence = "Low"

    return score, confidence


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
    processing_version="0.0.2",
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

    gdf["confidence_score"] = None
    gdf["confidence_class"] = None

    gdf["mean_vv_change_db"] = None
    gdf["mean_vh_change_db"] = None

    gdf["min_vv_change_db"] = None
    gdf["min_vh_change_db"] = None

    if change_vv is not None and change_vh is not None:

        for idx, row in gdf.iterrows():

            geom = [row.geometry]

            try:
                vv_clip = change_vv.rio.clip(
                    geom,
                    gdf.crs,
                    drop=True
                )

                vh_clip = change_vh.rio.clip(
                    geom,
                    gdf.crs,
                    drop=True
                )

                gdf.loc[idx, "mean_vv_change_db"] = float(
                    vv_clip.mean().values
                )

                gdf.loc[idx, "mean_vh_change_db"] = float(
                    vh_clip.mean().values
                )

                confidence_score, confidence_class = classify_confidence(
                    row["area_ha"],
                    float(vv_clip.mean().values),
                    float(vh_clip.mean().values)
                )

                gdf.loc[idx, "confidence_score"] = confidence_score
                gdf.loc[idx, "confidence_class"] = confidence_class

                gdf.loc[idx, "min_vv_change_db"] = float(
                    vv_clip.min().values
                )

                gdf.loc[idx, "min_vh_change_db"] = float(
                    vh_clip.min().values
                )

            except Exception as e:
                print(
                    f"Warning: Could not calculate "
                    f"change statistics for flood "
                    f"{row['flood_id']}: {e}"
                )
    
    # Export to file (GeoJSON or Shapefile depending on the extension provided)
    try:
        gdf.to_file(output_filename)
        print(f"Successfully exported {len(gdf)} polygons to: {output_filename}")
    except Exception as e:
        print(f"Vector export failed: {e}")
        
    return gdf