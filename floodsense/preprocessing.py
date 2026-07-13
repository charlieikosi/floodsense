from scipy.ndimage import median_filter
import xarray as xr

def apply_spatial_tuning(data_array, window_size=3):
    """
    Applies a memory-efficient 2D median filter to an xarray Dataset using SciPy.
    Handles multiple bands (vv, vh) independently.
    """
    print(f"Applying SciPy median filter (Window: {window_size}x{window_size})...")
    
    # 1. Create an empty Dataset to hold the smoothed variables
    smoothed_ds = xr.Dataset(coords=data_array.coords, attrs=data_array.attrs)
    
    # 2. Loop through each polarization band ('vv' and 'vh')
    for var_name in data_array.data_vars:
        
        # Extract the raw 2D numpy array for this specific band
        raw_values = data_array[var_name].values
        
        # Apply SciPy's filter
        smoothed_values = median_filter(raw_values, size=window_size)
        
        # Put the smoothed data back into a DataArray
        smoothed_ds[var_name] = xr.DataArray(
            smoothed_values,
            coords=data_array[var_name].coords,
            dims=data_array[var_name].dims
        )
        
    # 3. Ensure the CRS metadata survives for downstream functions
    smoothed_ds.rio.write_crs(data_array.rio.crs, inplace=True)
    
    return smoothed_ds


import geopandas as gpd
import odc.stac
import rioxarray

def load_and_crop_dual_pol(selected_item, aoi_input, resolution=10):
    """
    Loads both VV and VH polarizations. 
    Accepts either a file path (string) or a GeoDataFrame.
    """
    # 1. Handle Input Type: Load if path, otherwise use as GDF
    if isinstance(aoi_input, str):
        print(f"Loading shapefile from: {aoi_input}")
        aoi_gdf = gpd.read_file(aoi_input)
    else:
        aoi_gdf = aoi_input

    # 2. Ensure AOI is WGS84 for the STAC/ODC spatial query
    aoi_wgs84 = aoi_gdf.to_crs("EPSG:4326")

    # 3. Load Dual-Pol data using odc-stac
    ds = odc.stac.load(
        [selected_item],
        geopolygon=aoi_wgs84.geometry.iloc[0], 
        bands=["vv", "vh"], # Loading both polarizations here
        crs="EPSG:3857",
        resolution=resolution,
        chunks={"x": 512, "y": 512}
    )

    # 4. Squeeze time and extract the 2D array
    data_array = ds.squeeze()
    
    # 5. Exact geometric clip
    # Reproject AOI to match the data's CRS right before clipping
    aoi_projected = aoi_gdf.to_crs(data_array.rio.crs) 
    
    clipped_data = data_array.rio.clip(
        aoi_projected.geometry, 
        aoi_projected.crs, 
        drop=True
    )
    
    print(f"Successfully loaded and clipped dual-pol scene: {selected_item.id}")
    return clipped_data