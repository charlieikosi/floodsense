import os
import geopandas as gpd


def append_to_floodsense_database(
    current_gdf,
    gpkg_path,
    layer_name="flood_events"
):
    """
    Append flood polygons to the master
    FloodSense GeoPackage.
    """

    if current_gdf is None:
        return

    # First write
    if not os.path.exists(gpkg_path):

        current_gdf.to_file(
            gpkg_path,
            layer=layer_name,
            driver="GPKG"
        )

        print(
            f"Created FloodSense database: "
            f"{gpkg_path}"
        )

        return

    # Append records
    current_gdf.to_file(
        gpkg_path,
        layer=layer_name,
        driver="GPKG",
        mode="a"
    )

    print(
        f"Appended records to FloodSense database: "
        f"{gpkg_path}"
    )