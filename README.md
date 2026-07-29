# FloodSense

FloodSense is a Python toolkit for rapid flood detection and inundation mapping using Sentinel-1 SAR imagery and Microsoft Planetary Computer data.

The library provides an end-to-end workflow for flood mapping, including automated scene discovery, orbit-consistent image selection, SAR preprocessing, spatial noise reduction, permanent water masking, and change detection.

Designed for operational geospatial workflows, FloodSense helps transform satellite observations into reliable flood intelligence for emergency response, infrastructure assessment, and environmental monitoring.

## Key Features

- Automated Sentinel-1 RTC data discovery
- Microsoft Planetary Computer integration
- Orbit-aware SAR scene selection
- Spatial filtering and speckle reduction
- Permanent water masking using ESA WorldCover
- Scalable raster processing with xarray
- Flood extent generation and analysis

> From satellite imagery to actionable flood insights.

## Key Functions

### 1. get_rtc_catalog_items(shapefile_path, date_range)

**Purpose:** Discover Sentinel‑1 RTC imagery for an Area of Interest (AOI).

**What it does:**

- Loads the AOI shapefile.
- Reprojects the AOI to WGS84 (EPSG:4326).
- Creates a bounding box for STAC searches.
- Connects to the Microsoft Planetary Computer STAC API.
- Searches the sentinel-1-rtc collection within a specified date range.
- Returns matching STAC items and the AOI geometry.

**Role in workflow:** Data acquisition and scene discovery.

### 2. select_scenes_by_orbit(items, orbit_state="descending")

**Purpose:** Ensure SAR scenes are from a consistent orbit direction.

**What it does:**

- Filters STAC items by sat:orbit_state.
- Supports ascending or descending passes.
- Warns when no matching scenes are found.

**Why important:** Using the same orbit direction reduces geometric inconsistencies and false change signals in SAR-based flood mapping.

**Role in workflow:** Scene quality control.

### 3. select_scene_for_processing(items, index=0)

**Purpose:** Select a single image for analysis.

**What it does:**

- Sorts scenes by acquisition date.
- Chooses a scene by index.
- Retrieves acquisition metadata.
- Converts timestamps to New Zealand time for reporting and interpretation.

**Role in workflow:** Scene selection and metadata management.

### 4. apply_spatial_tuning(data_array, window_size=3)

**Purpose:** Reduce SAR speckle noise before flood detection.

**What it does:**

- Applies a 2D median filter using SciPy.
- Processes each polarization band independently (e.g., VV, VH).
- Preserves coordinates and CRS metadata.
- Returns a smoothed xarray dataset.

**Why important:** SAR imagery contains speckle noise that can create false flood detections. Median filtering improves signal quality while retaining edges.

**Role in workflow:** Image preprocessing.

### 5. apply_permanent_water_mask(flood_mask, aoi_gdf)

**Purpose:** Remove permanent water bodies from flood results.

**What it does:**

- Retrieves ESA WorldCover data from Planetary Computer.
- Loads the most recent land-cover dataset.
- Aligns the WorldCover raster with the flood mask.
- Masks oceans, lakes, and other permanent water features.
- Reduces false positives caused by pre-existing water.

**Role in workflow:** Post-processing and quality assurance.
