import rasterio.features
from shapely.geometry import shape
import geopandas as gpd

from datetime import datetime, timezone
import time

def classify_season(event_datetime):
    """
    Returns NZ season based on acquisition date.
    """

    month = event_datetime.month

    if month in [12, 1, 2]:
        return "Summer"

    elif month in [3, 4, 5]:
        return "Autumn"

    elif month in [6, 7, 8]:
        return "Winter"

    else:
        return "Spring"
   

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


def classify_status(
    confidence_score,
    area_ha,
    mean_vh_change_db,
    season,
    mean_elevation_m,
    mean_slope_deg
):
    """
    Operational interpretation of a flood detection.
    """

    # Likely snow or ice
    if (
        season == "Winter"
        and mean_elevation_m >= 500
    ):
        return "Possible Snow/Ice"

    # Steep terrain is suspicious
    elif (
        mean_slope_deg >= 10
    ):
        return "Possible Terrain Artefact"

    # Strong flood candidate
    elif (
        confidence_score >= 65
        and area_ha >= 5
        and mean_vh_change_db <= -4
    ):
        return "Likely Flooding"

    # Moderate flood candidate
    elif (
        confidence_score >= 40
        and mean_vh_change_db <= -3
    ):
        return "Potential Flooding"

    # Everything else
    else:
        return "Review Required"


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
    change_vh=None,
    dem=None,
    terrain_slope=None
):
    """
    Converts a binary xarray DataArray mask into a GeoDataFrame of polygons,
    keeping only the areas where the value is 1, and exports it.
    """

    # Start timer for performance logging
    start_time = time.time()

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

    # Season metadata
    gdf["month"] = None
    gdf["season"] = None

    if event_datetime is not None:

        event_dt = datetime.fromisoformat(
            event_datetime.replace("Z", "+00:00")
        )

        gdf["month"] = event_dt.month
        gdf["season"] = classify_season(event_dt)

    # Processing metadata
    gdf["baseline_scene_id"] = baseline_scene_id
    gdf["threshold_db"] = threshold_db
    gdf["smoothing_window"] = smoothing_window
    gdf["processing_version"] = processing_version

    # Operational metadata
    gdf["source"] = source
    gdf["status"] = None

    # Persistence
    gdf["persistence_count"] = 1
    gdf["persistence_class"] = "New"
    gdf["first_detected"] = event_date
    gdf["last_detected"] = event_date
    gdf["duration_days"] = 0
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

    # Terrain intelligence
    gdf["mean_elevation_m"] = None
    gdf["max_elevation_m"] = None

    gdf["mean_slope_deg"] = None
    gdf["max_slope_deg"] = None

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

                # Elevation statistics
                if dem is not None:

                    dem_clip = dem.rio.clip(
                        geom,
                        gdf.crs,
                        drop=True
                    )

                    gdf.loc[idx, "mean_elevation_m"] = float(
                        dem_clip.mean().values
                    )

                    gdf.loc[idx, "max_elevation_m"] = float(
                        dem_clip.max().values
                    )

                # Slope statistics
                if terrain_slope is not None:

                    slope_clip = terrain_slope.rio.clip(
                        geom,
                        gdf.crs,
                        drop=True
                    )

                    gdf.loc[idx, "mean_slope_deg"] = float(
                        slope_clip.mean().values
                    )

                    gdf.loc[idx, "max_slope_deg"] = float(
                        slope_clip.max().values
                    )

                gdf.loc[idx, "mean_vv_change_db"] = float(
                    vv_clip.mean().values
                )

                gdf.loc[idx, "mean_vh_change_db"] = float(
                    vh_clip.mean().values
                )

                mean_vv = float(vv_clip.mean().values)
                mean_vh = float(vh_clip.mean().values)

                confidence_score, confidence_class = classify_confidence(
                    row["area_ha"],
                    mean_vv,
                    mean_vh
                )

                gdf.loc[idx, "confidence_score"] = confidence_score
                gdf.loc[idx, "confidence_class"] = confidence_class

                status = classify_status(
                    confidence_score,
                    row["area_ha"],
                    mean_vh,
                    row["season"],
                    gdf.loc[idx, "mean_elevation_m"],
                    gdf.loc[idx, "mean_slope_deg"]
                )

                gdf.loc[idx, "status"] = status

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

    # Log the time taken for vectorization and export
    elapsed = time.time() - start_time
    print(f"Vector export completed in {elapsed:.1f} seconds.")
        
    return gdf