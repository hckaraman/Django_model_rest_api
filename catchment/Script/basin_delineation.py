import json
from geojson import Polygon
import numpy as np
from pysheds.grid import Grid
from pyproj import Proj, transform
import tarfile
from . import catchment_routine
import datetime
import sys
import os
import csv
from . import hyspoparser as hy
import pandas as pd

import geopandas as gpd
from shapely.geometry import Point
import whitebox
import rasterio
from rasterio.features import shapes as shp

# start_time = datetime.datetime.now()
# This version sends geojson data to
# node server instead of recording to the disk.
path = r"D:\Github\Django\catchment\Process"


# grid.read_raster('./misc/dir.tif', data_name='dir')
# grid.read_raster('./misc/acc.tif', data_name='acc')
# print('Read Finished : ', datetime.datetime.now()-start_time)
# ed-50 zone 36


def extract_and_retreive(tar_file):
    tf = tarfile.open(tar_file)
    comressed_dem_file_name = [row.name for row in tf.members][0]
    tf.extractall(path=os.path.dirname(tar_file))
    return comressed_dem_file_name


def read_in():
    lines = sys.stdin.readlines()
    return json.loads(lines[0])


def catch(x, y, upload_folder, user_folder, file_name):
    # x, y, upload_folder, user_folder, file_name = read_in()

    # x, y, upload_folder, user_folder, file_name = [638311.1290535209, 4148774.824472582, 'file_uploads',
    #                                                'bbbbb',
    #                                                'dem.tar.gz']

    if file_name == 'srtm_turkey':
        try:
            xy_cor = transform(Proj(init='epsg:3857'), Proj(
                init='epsg:23036'), *zip([float(x), float(y)]))
            x, y = xy_cor[0][0], xy_cor[1][0]
            print(xy_cor)
            print(x, y)
            start = datetime.datetime.now()
            # bas = catchment_routine.CreateCacthment(480189.932, 4100069.151)
            # bas = catchment_routine.CreateCacthment(664421.0251895901, 4124028.181024239)
            bas = catchment_routine.CreateCacthment(x, y)
            bas.process_path = path
            bas.basin_dem = os.path.join(bas.process_path, "DEM_ED50_re.tif")
            # bas.process_path = r  "./file_uploads/srtm"
            upload_path = "./file_uploads"
            bas.init_grid()
            bas.readwindow()
            bas.conditioning()
            # bas.resample()
            bas.calculate_flow_dir()
            bas.calculate_accumlation()
            bas.dem_export(os.path.join(upload_path, user_folder))
            bas.snaptoacc()
            bas.snap_xy()
            ccc = bas.run_for_catchment()
            bas.to_shape(os.path.join(upload_path, user_folder))
            end = datetime.datetime.now() - start

        except BaseException as be:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)
            with open("python_err_log.csv", "a") as c_file:
                c_writer = csv.writer(c_file)
                c_writer.writerow([be.message])
                c_writer.writerow(["error"])
    else:
        file_name = extract_and_retreive(
            os.path.join(path, file_name))

        xnew = x
        ynew = y

        point_geom = Point(float(xnew), float(ynew))
        point = gpd.GeoDataFrame(
            index=[0], crs='epsg:23036', geometry=[point_geom])
        point.to_file(filename=os.path.join(
            path, "point.shp"), driver="ESRI Shapefile")

        wbt = whitebox.WhiteboxTools()
        wbt.set_verbose_mode(False)
        wbt.work_dir = path
        at = path

        wbt.breach_depressions("dem.tif", "DEM_breach.tif")
        wbt.fill_depressions("DEM_breach.tif", "DEM_fill.tif")
        wbt.flow_accumulation_full_workflow(
            "DEM_fill.tif", "DEM_out.tif", "Flow_dir.tif", "Flow_acc.tif", log=False)
        # wbt.basins("Flow_dir.tif", "Basins.tif")
        # wbt.extract_streams("Flow_acc.tif", "streams.tif", threshold=-1)
        # wbt.find_main_stem(
        #     "Flow_dir.tif", "streams.tif", "main_stream.tif")
        # wbt.raster_streams_to_vector(
        #     "streams.tif", "Flow_dir.tif", "riverswht.shp")
        # wbt.raster_streams_to_vector(
        #     "main_stream.tif", "Flow_dir.tif", "main_stream.shp")
        # wbt.horton_stream_order(
        #     "Flow_dir.tif", "streams.tif", "Horton.tif")
        # wbt.strahler_stream_order(
        #     "Flow_dir.tif", "streams.tif", "Strahler.tif")
        # wbt.raster_streams_to_vector(
        #     "Horton.tif", "Flow_dir.tif", "Horton.shp")
        # wbt.raster_streams_to_vector(
        #     "Strahler.tif", "Flow_dir.tif", "Strahler.shp")
        wbt.snap_pour_points("point.shp", "Flow_acc.tif",
                             "snap_point.shp", snap_dist=200)
        wbt.watershed("Flow_dir.tif", "snap_point.shp", "Watershed.tif")
        mask = None
        with rasterio.open(os.path.join(at, "Watershed.tif")) as src:
            image = src.read(1)  # first band
            results = (
                {'properties': {'raster_val': v}, 'geometry': s}
                for i, (s, v)
                in enumerate(
                shp(image, mask=mask, transform=src.transform)))

        geoms = list(results)
        boundary = shp(geoms[0]['geometry'])
        gpd_polygonized_raster = gpd.GeoDataFrame.from_features(geoms)
        # Filter nodata value
        gpd_polygonized_raster = gpd_polygonized_raster[gpd_polygonized_raster['raster_val'] == 1]
        # Convert to geojson

        gpd_polygonized_raster.crs = 'epsg:23036'
        gpd_polygonized_raster.to_file(
            driver='ESRI Shapefile', filename=os.path.join(at, "basin_boundary_23063.shp"))

        gpd_polygonized_raster = gpd_polygonized_raster.to_crs(
            'epsg:4326')  # world.to_crs(epsg=3395) would also work
        gpd_polygonized_raster.to_file(
            driver='ESRI Shapefile', filename=os.path.join(at, "basin_boundary.shp"))

        wbt.clip_raster_to_polygon(
            "DEM_out.tif", "basin_boundary_23063.shp", "DEM_watershed.tif")
        wbt.hypsometric_analysis("DEM_watershed.tif", "hypso.html")
        #wbt.slope_vs_elevation_plot(
        #    "DEM_watershed.tif", "Slope_elevation.html")
        wbt.zonal_statistics(
            "DEM_out.tif", "Watershed.tif", output=None, stat="total", out_table="stat.html")
        #wbt.raster_histogram("DEM_watershed.tif", "hist.html")

        gpd_polygonized_raster["area"] = gpd_polygonized_raster['geometry'].area
        Area = gpd_polygonized_raster['geometry'].area * 10000
        Area = Area.max()
        try:
            Centroid = [gpd_polygonized_raster.centroid.x[1], gpd_polygonized_raster.centroid.y[1]]
        except:
            Centroid = [gpd_polygonized_raster.centroid.x[0], gpd_polygonized_raster.centroid.y[0]]
        boundary = gpd_polygonized_raster.to_json()

        y = json.loads(boundary)
        # data = boundary['features'][0]['geometry']['coordinates']

        # logfile2.write(str(y['features'][0]['geometry']['coordinates']))

        data = y['features'][0]['geometry']['coordinates']

        try:
            if y['features'][1]['geometry']['coordinates'].__str__().__sizeof__() > data.__str__().__sizeof__():
                boundary = Polygon(y['features'][1]['geometry']['coordinates'])
            else:
                boundary = Polygon(data)
        except:
            boundary = Polygon(data)

        X, Y = hy.hypso(os.path.join(at, "hypso.html"))
        stat = hy.stat(os.path.join(at, "stat.html"))
        # logfile = open(
        #     r'D:\Github\model_experiment\NAM\datadir\basin_log33.txt', 'a+')
        # logfile.write(str(stat))
        basin_object = []
        text = "at"
        hypsometry = []
        hypsometry.append(X)
        hypsometry.append(Y)

        df_res = pd.DataFrame()
        df_res['X'] = X
        df_res['Y'] = Y
        j = df_res.to_json(orient='records')
        basin_object.append({"Polygon": json.dumps(boundary),
                             "hypso": j,
                             "stats": json.dumps(stat),
                             "status": 'success',
                             "Area": json.dumps(Area),
                             "Centroid": json.dumps(Centroid)})
        basin_object.append({"Polygon": json.dumps(boundary)})
        basin_object = json.dumps(basin_object)
        return basin_object


if __name__ == '__main__':
    x = catch(638311.1290535209, 4148774.824472582, 'file_uploads',
              'bbbbb',
              'dem.tar.gz')
