import numpy as np

def export_to_geotiff(data_array, filename="sar_change_result.tif"):
    """
    Exports an xarray DataArray to a standard GeoTIFF file.
    Works for both continuous dB change maps and binary masks.
    """
    # 1. Ensure the data has a CRS defined
    # If the CRS was lost during math operations, we ensure it's set before writing
    if data_array.rio.crs is None:
        print("Warning: CRS not found. Attempting to set default EPSG:3857.")
        data_array.rio.write_crs("EPSG:3857", inplace=True)

    # 2. Export to GeoTIFF
    # 'GTiff' is the standard driver.
    # We use 'nodata=np.nan' for float data (dB maps) 
    # or a specific integer (like 0 or 255) for binary masks.
    try:
        data_array.rio.to_raster(
            filename,
            driver="GTiff",
            nodata=np.nan 
        )
        print(f"Successfully exported result to: {filename}")
    except Exception as e:
        print(f"Export failed: {e}")