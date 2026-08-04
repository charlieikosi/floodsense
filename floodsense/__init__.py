"""
FloodSense
==========

FloodSense is a Python toolkit for automated flood detection and inundation
mapping using Sentinel-1 SAR imagery and Microsoft Planetary Computer data.

The package provides tools for:

- Sentinel-1 RTC scene discovery
- Orbit-aware scene filtering
- Dual-polarization SAR loading and clipping
- SAR preprocessing and speckle reduction
- SSIM-based change detection
- Wind-aware flood detection
- Terrain masking
- Permanent water masking
- GeoTIFF export
- Flood polygon generation
"""

from .__version__ import __version__

# Catalog / Scene Discovery
from .catalog import (
    get_rtc_catalog_items,
    select_scenes_by_orbit,
    select_scene_for_processing,
)

# Data Loading & Preprocessing
from .preprocessing import (
    load_and_crop_dual_pol,
    apply_spatial_tuning,
)

# Change Detection
from .change_detection import (
    calculate_ssim_change,
    calculate_wind_aware_mask,
    calculate_dual_pol_change_db,
)

# Flood Mask Refinement
from .masking import (
    apply_binary_median_filter,
    apply_terrain_mask,
    apply_permanent_water_mask,
)

# Raster Outputs
from .io import (
    export_to_geotiff,
)

# Vector Outputs
from .vector import (
    export_mask_to_polygons,
)

# Event Persistence
from .persistence import (
    classify_persistence,
    load_previous_polygons,
    find_matching_polygon,
    update_persistence,
    find_previous_geojson,
)

__all__ = [
    # Catalog
    "get_rtc_catalog_items",
    "select_scenes_by_orbit",
    "select_scene_for_processing",

    # Preprocessing
    "load_and_crop_dual_pol",
    "apply_spatial_tuning",

    # Change Detection
    "calculate_ssim_change",
    "calculate_wind_aware_mask",
    "calculate_dual_pol_change_db",

    # Masking
    "apply_binary_median_filter",
    "apply_terrain_mask",
    "apply_permanent_water_mask",

    # Outputs
    "export_to_geotiff",
    "export_mask_to_polygons",

    # Event Persistence
    "classify_persistence",
    "load_previous_polygons",
    "find_matching_polygon",
    "update_persistence",
    "find_previous_geojson",

    # Metadata
    "__version__",
]