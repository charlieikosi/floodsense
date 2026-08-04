# FloodSense

FloodSense is a Python toolkit for automated flood detection, flood intelligence, and event persistence monitoring using Sentinel-1 SAR imagery and Microsoft Planetary Computer data.

FloodSense automates the discovery, preprocessing, filtering, and analysis of Sentinel-1 Synthetic Aperture Radar (SAR) imagery to generate flood extent maps while reducing false detections through orbit-aware processing, terrain masking, permanent water screening, confidence scoring, and event persistence tracking.

---

## Features

### Sentinel-1 SAR Processing

- Sentinel-1 RTC scene discovery
- Orbit-aware scene filtering
- Automated AOI clipping
- Dual-polarisation (VV/VH) SAR processing
- Speckle reduction and smoothing

### Flood Detection

- Dual-polarisation change detection
- Wind-aware flood detection
- Binary noise filtering
- Terrain masking
- Permanent water masking

### Flood Intelligence

- Confidence scoring
- Flood severity classification
- Flood status classification
- Seasonal intelligence
- Terrain intelligence
- Snow and terrain artefact flagging

### Event Persistence

FloodSense can track flood events through time.

Features include:

- Persistence count
- Persistence classification
- First detected date
- Last detected date
- Event duration tracking

### Outputs

- GeoTIFF flood extent rasters
- GeoJSON flood polygons
- Detailed flood intelligence attributes

---

# Installation

Install directly from GitHub:

```bash
pip install git+https://github.com/charlieikosi/floodsense.git
```

Or clone locally:

```bash
git clone https://github.com/charlieikosi/floodsense.git

cd floodsense

pip install -e .
```

---

# Dependencies

FloodSense relies on:

```text
planetary-computer
pystac-client
geopandas
rioxarray
xarray
rasterio
numpy
scipy
shapely
pyproj
```

Install all dependencies with:

```bash
pip install -r requirements.txt
```

---

# Workflow Overview

FloodSense follows the workflow below:

```text
Baseline Scene
       ↓
Target Scene
       ↓
VV/VH Change Detection
       ↓
Wind-Aware Flood Detection
       ↓
Binary Noise Reduction
       ↓
Terrain Masking
       ↓
Permanent Water Masking
       ↓
Flood Polygon Generation
       ↓
Confidence Scoring
       ↓
Status Classification
       ↓
Terrain Intelligence
       ↓
Event Persistence Tracking
```

---

# Configuration

The workflow is controlled through a small set of configuration variables.

Example:

```python
AOI = r"C:\path\to\AOI.shp"

BASELINE_SCENE_ID = (
    "S1A_IW_GRDH_1SDV_20250419T073047_20250419T073116_058822_rtc"
)

TARGET_DATE_RANGE = "2025-04-20/2025-05-08"

ORBIT_STATE = "ascending"

THRESHOLD_VAL = -2.5

SMOOTHING_WINDOW = 17

OUTPUT_DIR = "./output_payloads"
```

---

## AOI

AOI must be a polygon shapefile defining the area of interest.

Example:

```python
AOI = r"C:\data\Canterbury_AOI.shp"
```

### Required Fields

FloodSense expects a monitoring identifier field:

```text
gridID
```

Example:

```text
gridID

A1-Whitianga
CHC-001
NRC-002
```

This field is used to generate unique output filenames.

---

## Baseline Scene

Provide a Sentinel-1 RTC scene ID to use as the flood-free reference scene.

Example:

```python
BASELINE_SCENE_ID = (
    "S1C_IW_GRDH_1SDV_20260405T070704_20260405T070729_007077_00E551_rtc"
)
```

The baseline should represent typical non-flood conditions.

---

## Target Date Range

Specify the monitoring period.

Example:

```python
TARGET_DATE_RANGE = "2026-07-01/2026-07-31"
```

FloodSense automatically searches for Sentinel-1 RTC scenes within this period.

---

## Orbit State

To minimise SAR viewing angle differences:

```python
ORBIT_STATE = "ascending"
```

Supported values:

```text
ascending
descending
```

---

## Detection Threshold

Flood detection threshold in decibels.

Example:

```python
THRESHOLD_VAL = -2.5
```

Typical values:

```text
-2.0
-2.5
-3.0
```

---

## Smoothing Window

Median filter size used for SAR speckle reduction.

Example:

```python
SMOOTHING_WINDOW = 17
```

---

# Running FloodSense

Example:

```python
from floodsense import *
```

Follow the workflow:

```python
target_items, my_aoi = get_rtc_catalog_items(
    AOI,
    TARGET_DATE_RANGE
)

target_items = select_scenes_by_orbit(
    target_items,
    orbit_state="ascending"
)
```

Load data:

```python
data_baseline = load_and_crop_dual_pol(
    baseline_scene,
    AOI
)
```

Calculate change:

```python
change_vv, change_vh = (
    calculate_dual_pol_change_db(
        data_baseline,
        data_current
    )
)
```

Generate flood masks:

```python
wind_aware_flood_mask =
    calculate_wind_aware_mask(...)
```

Export flood products:

```python
export_to_geotiff(...)
export_mask_to_polygons(...)
```

---

# Output Naming

Outputs use the AOI Grid ID.

Example:

```text
A1-Whitianga_flood_ext_2026-07-12.tif

A1-Whitianga_flood_ext_2026-07-12.geojson
```

This prevents conflicts between multiple monitoring locations.

---

# Output Attributes

Every flood polygon includes the following attributes.

---

## Event Metadata

```text
event_date
event_datetime
scene_id
orbit_state
```

---

## Processing Metadata

```text
baseline_scene_id
threshold_db
smoothing_window
processing_version
processed_utc
```

---

## Flood Characteristics

```text
area_m2
area_ha
area_km2

severity
```

Severity Classes:

```text
Low
Medium
High
```

---

## SAR Evidence

```text
mean_vv_change_db
mean_vh_change_db

min_vv_change_db
min_vh_change_db
```

---

## Confidence

FloodSense calculates a confidence score using:

- VH change
- VV change
- Flood area

Outputs:

```text
confidence_score
confidence_class
```

Confidence Classes:

```text
Low
Medium
High
Very High
```

---

## Seasonal Intelligence

```text
month
season
```

Possible values:

```text
Summer
Autumn
Winter
Spring
```

---

## Terrain Intelligence

```text
mean_elevation_m
max_elevation_m

mean_slope_deg
max_slope_deg
```

Derived from Copernicus DEM.

---

## Flood Status

Operational interpretation of each detection.

Possible values:

```text
Likely Flooding

Potential Flooding

Review Required

Possible Snow/Ice

Possible Terrain Artefact
```

---

## Event Persistence

FloodSense tracks flood events through time.

Attributes:

```text
persistence_count

persistence_class

first_detected

last_detected

duration_days
```

Persistence Classes:

```text
New

Persistent

Long Duration
```

---

# Confidence Scoring

Confidence scores are calculated using:

```text
VH Change (0–50 points)

VV Change (0–30 points)

Flood Area (0–20 points)
```

Maximum score:

```text
100
```

Confidence classes:

```text
85–100  → Very High

65–84   → High

40–64   → Medium

0–39    → Low
```

---

# Event Persistence

FloodSense tracks flood events across consecutive acquisitions using polygon overlap analysis.

Floods are considered persistent when:

```text
Polygon overlap >= 50%
```

between subsequent observations.

Metrics include:

```text
Persistence Count

Duration Days

First Detected

Last Detected
```

---

# Current Limitations

- Event persistence is based on consecutive acquisitions
- Snow/terrain flagging is currently rule-based
- Persistence tracks flood events rather than long-term flood recurrence
- Confidence scoring uses empirical thresholds that may require regional calibration

---

# License

MIT License

---

# Acknowledgements

FloodSense uses:

- Sentinel-1 SAR imagery
- Microsoft Planetary Computer
- Copernicus DEM
- ESA WorldCover

to support automated flood monitoring and flood intelligence workflows.