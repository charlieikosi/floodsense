import xarray as xr
import odc.stac
import pystac_client
import planetary_computer

def apply_permanent_water_mask(flood_mask, aoi_gdf):
    """
    Fetches the latest ESA WorldCover 10m dataset to mask out the ocean, sea, 
    and permanent lakes. Prevents false positive floods over existing water.
    """
    print("Fetching ESA WorldCover to mask out oceans and permanent water...")
    
    # 1. Connect to Planetary Computer STAC
    catalog = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace
    )
    
    # 2. Search for ESA WorldCover using your WGS84 AOI bounds
    bounds = list(aoi_gdf.to_crs("EPSG:4326").total_bounds)
    search = catalog.search(
        collections=["esa-worldcover"],
        bbox=bounds
    )
    wc_items = search.item_collection()
    
    if len(wc_items) == 0:
        print("Warning: No WorldCover data found. Returning original mask.")
        return flood_mask

    # --- THE FIX: Sort by start_datetime since composite maps lack a specific datetime ---
    wc_items = sorted(
        wc_items, 
        key=lambda x: x.properties.get("start_datetime", ""), 
        reverse=True
    )
    
    # 3. Load ONLY the most recent Land Cover Map
    wc_ds = odc.stac.load(
        [wc_items[0]], # Force it to load 1 item, preventing the 3D time-stack
        bbox=bounds,
        crs=flood_mask.rio.crs,
        resolution=10, 
        resampling="nearest" 
    ).squeeze() # Squeeze will now successfully drop the single time dimension
    
    # 4. Pixel-Perfect Alignment
    wc_aligned = wc_ds["map"].rio.reproject_match(flood_mask)
    
    # 5. Create a Land-Only Mask (1 = Land, 0 = Permanent Water)
    land_only_mask = xr.where(wc_aligned != 80, 1, 0)
    
    # 6. Apply the Mask
    final_land_flood_mask = flood_mask * land_only_mask
    
    # Preserve metadata
    final_land_flood_mask.rio.write_crs(flood_mask.rio.crs, inplace=True)
    
    # Logging
    removed_pixels = int((flood_mask.sum() - final_land_flood_mask.sum()).values)
    print(f"Water mask successfully removed {removed_pixels} ocean/lake pixels.")
    
    return final_land_flood_mask


import xarray as xr
import odc.stac
import pystac_client
import planetary_computer
from xrspatial import slope

def apply_terrain_mask(flood_mask, aoi_gdf, max_slope_degrees=5.0):
    """
    Fetches Copernicus DEM, calculates topographic slope, and removes 
    any flagged flood pixels that occur on terrain steeper than the threshold.
    """
    print(f"Fetching Copernicus DEM to mask slopes > {max_slope_degrees}°...")
    
    # 1. Connect to Planetary Computer STAC
    catalog = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace
    )
    
    # 2. Search for the DEM using the WGS84 AOI bounds
    bounds = list(aoi_gdf.to_crs("EPSG:4326").total_bounds)
    search = catalog.search(
        collections=["cop-dem-glo-30"],
        bbox=bounds
    )
    dem_items = search.item_collection()
    
    if len(dem_items) == 0:
        print("Warning: No DEM found for this AOI. Returning original mask.")
        return flood_mask

    # 3. Load the DEM using odc.stac
    # CRITICAL FIX: Added bilinear resampling to prevent stair-step artifacts
    # when upsampling 30m DEM to 10m SAR resolution.
    dem_ds = odc.stac.load(
        dem_items,
        bbox=bounds,
        crs=flood_mask.rio.crs,
        resolution=10, 
        resampling="bilinear" 
    ).squeeze()
    
    # 4. Pixel-Perfect Alignment
    # Reproject and clip the DEM so its grid perfectly matches the SAR flood mask
    dem_aligned = dem_ds.data.rio.reproject_match(flood_mask)
    
    print("Calculating geomorphological slope...")
    # 5. Calculate Slope
    # xrspatial calculates the gradient in degrees
    terrain_slope = slope(dem_aligned)
    
    # 6. Create Binary Valid Terrain Mask (1 = flat enough for water, 0 = too steep)
    valid_terrain_mask = xr.where(terrain_slope <= max_slope_degrees, 1, 0)
    
    # 7. Apply the Mask
    # Bitwise AND to keep only pixels that are FLOODED (1) AND FLAT (1)
    terrain_corrected_mask = flood_mask * valid_terrain_mask
    
    # Preserve metadata for AWS/Firebase export pipelines[cite: 4]
    terrain_corrected_mask.rio.write_crs(flood_mask.rio.crs, inplace=True)
    
    # Optional: Calculate how many false positives were removed for your logging
    removed_pixels = int((flood_mask.sum() - terrain_corrected_mask.sum()).values)
    print(f"Terrain filter successfully removed {removed_pixels} false positive pixels.")
    
    return (
    terrain_corrected_mask,
    dem_aligned,
    terrain_slope
)


def apply_binary_median_filter(binary_mask, window_size=3):
    """
    Cleans up the 'salt and pepper' noise from a binary change map.
    
    Parameters:
    - binary_mask: The 0/1 xarray DataArray from the thresholding step.
    - window_size: Size of the filter (3 is standard, 5 for very noisy data).
    """
    print(f"Applying {window_size}x{window_size} median filter to clean binary map...")
    
    # We use the rolling window median. 
    # For a binary map (0s and 1s), the median acts as a 'majority vote'.
    cleaned_mask = binary_mask.rolling(
        x=window_size, 
        y=window_size, 
        center=True, 
        min_periods=1
    ).median()
    
    # Ensure the result remains as integers (0 and 1)
    cleaned_mask = cleaned_mask.astype("uint8")
    
    # Preserve spatial metadata
    cleaned_mask.rio.write_crs(binary_mask.rio.crs, inplace=True)
    
    print("Post-processing complete.")
    return cleaned_mask