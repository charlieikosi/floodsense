from skimage.metrics import structural_similarity
import numpy as np
import xarray as xr

def calculate_ssim_change(data_before, data_after, window_size=7):
    """
    Calculates the Structural Similarity Index between two dates.
    Returns a 'Difference Map' where 1 = Complete Change, 0 = No Change.
    """
    print(f"Calculating SSIM (Window: {window_size}x{window_size})...")
    
    # 1. Extract raw numpy arrays from xarray
    arr_before = np.nan_to_num(data_before.values)
    arr_after = np.nan_to_num(data_after.values)
    
    # 2. Normalize arrays to a 0-1 scale for accurate SSIM contrast comparison
    b_max, a_max = arr_before.max(), arr_after.max()
    arr_before_norm = arr_before / b_max if b_max > 0 else arr_before
    arr_after_norm = arr_after / a_max if a_max > 0 else arr_after

    # 3. Compute SSIM
    # full=True returns the actual spatial map, not just a single average number
    score, ssim_map = structural_similarity(
        arr_before_norm, 
        arr_after_norm, 
        win_size=window_size,
        data_range=1.0, 
        full=True
    )
    
    # 4. Convert SSIM to a Difference Map
    # SSIM returns 1 for identical, 0 for totally different.
    # We invert it (1 - SSIM) so that high values = high change.
    difference_map = 1 - ssim_map
    
    # 5. Pack back into an xarray DataArray with original spatial coordinates
    ssim_xr = xr.DataArray(
        difference_map,
        coords=data_before.coords,
        dims=data_before.dims
    )
    ssim_xr.rio.write_crs(data_before.rio.crs, inplace=True)
    
    print(f"SSIM processing complete. Average similarity score: {score:.2f}")
    return ssim_xr


def calculate_wind_aware_mask(data_before, data_after, threshold_db=-2.5):
    """
    Calculates change for VV and VH while explicitly accounting for 
    wind-roughened floodwaters that cause VV false negatives.
    """
    print("Calculating Wind-Aware Dual-Pol Flood Mask...")
    
    # Calculate Log-Ratio for both polarizations
    change_vv = 10 * np.log10(data_after.vv / data_before.vv)
    change_vh = 10 * np.log10(data_after.vh / data_before.vh)
    
    # CONDITION 1: Calm conditions
    # Both polarizations drop below the standard threshold.
    mask_calm = (change_vv <= threshold_db) & (change_vh <= threshold_db)
    
    # CONDITION 2: Windy conditions (The fix)
    # The surface is flooded but wind causes Bragg scattering, keeping VV bright.
    # We require a slightly stricter VH drop (e.g., an extra 1 dB) to trust it without VV's confirmation.
    mask_windy = (change_vh <= (threshold_db - 1.0)) & (change_vv > threshold_db)
    
    # Combine the logic using bitwise OR
    robust_mask_boolean = mask_calm | mask_windy
    
    # Convert back to binary 1/0 integer array for the AWS/Firebase export pipeline
    robust_mask = xr.where(robust_mask_boolean, 1, 0)
    
    # Preserve metadata to prevent downstream projection errors
    robust_mask.rio.write_crs(data_before.rio.crs, inplace=True)
    
    return robust_mask