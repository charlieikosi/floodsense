import geopandas as gpd
from datetime import datetime

def ensure_persistence_fields(gdf):

    defaults = {
        "persistence_count": 1,
        "persistence_class": "New",
        "first_detected": None,
        "last_detected": None,
        "duration_days": 0
    }

    for field, value in defaults.items():

        if field not in gdf.columns:
            gdf[field] = value

    return gdf


def classify_persistence(count):
    """
    Classifies the persistence of a flood event based on the number of detections.
    """
    if count >= 4:
        return "Long Duration"
    elif count >= 2:
        return "Persistent"
    else:
        return "New"

def load_previous_polygons(path):
    """
    Loads previously detected flood polygons from a GeoPackage or Shapefile.
    Returns a GeoDataFrame or None if the file does not exist.
    """
    return gpd.read_file(path)


def find_matching_polygon(
    current_polygon,
    previous_gdf,
    threshold=0.5
):
    """
    Find the best matching flood polygon
    from the previous acquisition.

    Parameters
    ----------
    current_polygon : shapely.geometry
        Current flood polygon.

    previous_gdf : GeoDataFrame
        Previous flood layer.

    threshold : float
        Minimum overlap fraction required
        to consider polygons the same flood.

    Returns
    -------
    best_match : pandas.Series | None
        Matching previous polygon row.
    """

    best_match = None
    best_overlap = 0.0

    for _, previous_row in previous_gdf.iterrows():

        previous_polygon = previous_row.geometry

        # Skip if polygons do not touch
        if not current_polygon.intersects(
            previous_polygon
        ):
            continue

        intersection_area = (
            current_polygon
            .intersection(previous_polygon)
            .area
        )

        if current_polygon.area == 0:
            continue

        overlap_fraction = (
            intersection_area /
            current_polygon.area
        )

        if (
            overlap_fraction > best_overlap
            and overlap_fraction >= threshold
        ):

            best_overlap = overlap_fraction
            best_match = previous_row

    return best_match

def update_persistence(
    current_gdf,
    previous_gdf
):
    """
    Update flood persistence attributes by
    comparing current polygons with a
    previous flood layer.
    """

    # Ensure persistence fields exist

    previous_gdf = ensure_persistence_fields(
        previous_gdf
        )

    current_gdf = ensure_persistence_fields(
        current_gdf
        )

    for idx, row in current_gdf.iterrows():

        current_polygon = row.geometry

        match = find_matching_polygon(
            current_polygon,
            previous_gdf
        )

        # ----------------------
        # MATCH FOUND
        # ----------------------
        if match is not None:

            previous_count = int(
                match.get(
                    "persistence_count",
                    1
                )
            )

            first_detected = str(
                match.get(
                    "first_detected",
                    match["event_date"]
                )
            ).split(" ")[0]

            current_date = str(
                row["event_date"]
            ).split(" ")[0]

            print(
                f"first_detected={first_detected} "
                f"type={type(first_detected)}"
            )

            print(
                f"current_date={current_date} "
                f"type={type(current_date)}"
            )

            first_dt = datetime.strptime(
                first_detected,
                "%Y-%m-%d"
            )

            current_dt = datetime.strptime(
                current_date,
                "%Y-%m-%d"
            )

            duration_days = (
                current_dt - first_dt
            ).days

            new_count = previous_count + 1

            current_gdf.loc[
                idx,
                "persistence_count"
            ] = new_count

            current_gdf.loc[
                idx,
                "persistence_class"
            ] = classify_persistence(
                new_count
            )

            current_gdf.loc[
                idx,
                "first_detected"
            ] = first_detected

            current_gdf.loc[
                idx,
                "last_detected"
            ] = current_date

            current_gdf.loc[
                idx,
                "duration_days"
            ] = duration_days

        # ----------------------
        # NEW FLOOD
        # ----------------------
        else:

            current_date = row["event_date"]

            current_gdf.loc[
                idx,
                "persistence_count"
            ] = 1

            current_gdf.loc[
                idx,
                "persistence_class"
            ] = "New"

            current_gdf.loc[
                idx,
                "first_detected"
            ] = current_date

            current_gdf.loc[
                idx,
                "last_detected"
            ] = current_date

            current_gdf.loc[
                idx,
                "duration_days"
            ] = 0

    return current_gdf


import os
from datetime import datetime


def find_previous_geojson(
    current_date,
    output_dir
):
    """
    Find the most recent GeoJSON that
    predates the current acquisition.
    """

    geojson_files = []

    for filename in os.listdir(output_dir):

        if (
            filename.startswith("flood_ext_")
            and filename.endswith(".geojson")
        ):

            try:

                file_date = datetime.strptime(
                    filename.replace(
                        "flood_ext_",
                        ""
                    ).replace(
                        ".geojson",
                        ""
                    ),
                    "%Y-%m-%d"
                )

                geojson_files.append(
                    (
                        file_date,
                        os.path.join(
                            output_dir,
                            filename
                        )
                    )
                )

            except ValueError:
                continue

    current_dt = datetime.strptime(
        current_date,
        "%Y-%m-%d"
    )

    previous_files = [

        (date, path)

        for date, path in geojson_files

        if date < current_dt
    ]

    if not previous_files:
        return None

    previous_files.sort(
        key=lambda x: x[0]
    )

    return previous_files[-1][1]

