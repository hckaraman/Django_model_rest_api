"""
Class to read TR SRTM Data, extract river network, digitize catchment boundary

Methods
=======
init_grid :             Reads SRTM Data for TR
readwindow :            Creates a window with user specified coordinates at the center and reads the data
                        size of the window is specified with distance/2 in km
conditioning:           DEM conditioning (resolves pits, depressions, flats)
resample :              Resample DEM to specified resolution (Not working!!)
calculate_flow_dir :    Flow direction calculation
calculate_flow_acc :    Flow accumulation calculation
demexport :             Exports clipped , conditioned dem + flow direction , flow accumulation
                        in Geotiff to working directory
snaptoacc :             Finds the highest accumulation in data and snaps x,y coordinates
                        calculates river network in data with specified treshold (theshold will be selected)
to_shape :              Writes river network to shapefile
snap_xy :               Snaps to nearest high accumulation


"""

import numpy as np
import datetime
import matplotlib.pyplot as plt
from pysheds.grid import Grid
import fiona
import os
from pyproj import Proj, transform
import csv
import sys
import json
import tarfile


class CreateCacthment(object):
    def __init__(self, x, y, cond=True):
        self._working_directory = None
        self.basin_dem = None
        self.distance = 100
        self.window = None
        self.basin_data_dem_name = "dem"
        self.direction_map = (64, 128, 1, 2, 4, 8, 16, 32)
        self.dep = 'dep'
        self.flat = 'flat'
        self.pit = 'pit'
        self.output_name_dir = "dir"
        self.output_name_acc = "acc"
        self.output_name_catch = "catch"
        self.output_name_catch_sub = "catch_sub"
        self.x = x
        self.y = y
        self.x_coordinate = x
        self.y_coordinate = y
        self.grid = None
        self.snapx = None
        self.snapy = None
        self.cond = cond
        self.window = None
        self.branches = None

    @staticmethod
    def read_in():
        lines = sys.stdin.readlines()
        return json.loads(lines[0])

    @property
    def process_path(self):
        return self._working_directory

    @process_path.setter
    def process_path(self, value):
        self._working_directory = value
        pass

    def init_grid(self):

        self.grid = Grid.from_raster(
            self.basin_dem, data_name=self.basin_data_dem_name)

    def readwindow(self):
        self.window = (
            self.x - self.distance * 0.5 * 1e3, self.y - self.distance *
            0.5 * 1e3, self.x + self.distance * 0.5 * 1e3,
            self.y + self.distance * 0.5 * 1e3)
        self.grid.set_bbox(self.window)
        self.grid.read_raster(self.basin_dem, data_name=self.basin_data_dem_name, window=self.grid.bbox,
                              window_crs=self.grid.crs)

    def conditioning(self):
        self.grid.fill_pits(data=self.basin_data_dem_name, out_name=self.pit)
        self.grid.fill_depressions(data=self.pit, out_name=self.dep)
        self.grid.resolve_flats(data=self.dep, out_name=self.flat)

    def resample(self):
        s = self.grid.flat.shape
        s1 = int(int(s[0] / 4))
        s2 = int(int(s[1] / 4))
        self.grid.resize(data=self.flat, new_shape=(s1, s2))

    def calculate_flow_dir(self):
        self.grid.flowdir(
            data=self.flat, out_name=self.output_name_dir, dirmap=self.direction_map)

    def calculate_accumlation(self):
        self.grid.accumulation(data=self.output_name_dir,
                               out_name=self.output_name_acc)

    @staticmethod
    def check_and_make_dir(folder_name):
        if os.path.exists(folder_name):
            return True
        else:
            os.makedirs(folder_name)
            return True

    @staticmethod
    def make_tarfile(output_filename, source_dir):
        with tarfile.open(output_filename, "w:gz") as tar:
            tar.add(source_dir)

    def dem_export(self, path_):

        # self.grid.view(self.flat)
        # self.grid.to_raster(self.flat, os.path.join(self.process_path, "Flat.tif"), blockxsize=16, blockysize=16)
        if self.check_and_make_dir(path_):
            self.grid.to_raster(self.flat, os.path.join(
                path_, "dem.tif"), blockxsize=16, blockysize=16)
            self.make_tarfile(os.path.join(path_, "dem.tar.gz"),
                              os.path.join(path_, "dem.tif"))
        # self.grid.to_raster(self.acc, os.path.join(self.process_path, "Acc.tif"), blockxsize=16, blockysize=16)

    def snaptoacc(self):
        y, x = np.unravel_index(np.argsort(
            self.grid.acc.ravel())[-2], self.grid.acc.shape)
        self.grid.catchment(x, y, data=self.output_name_dir, out_name=self.output_name_catch,
                            dirmap=self.direction_map, xytype='index')
        self.branches = self.grid.extract_river_network(
            self.output_name_catch, self.output_name_acc, threshold=200)
        fig, ax = plt.subplots(figsize=(6.5, 6.5))

        plt.grid('on', zorder=0)
        plt.xlabel('Longitude')
        plt.ylabel('Latitude')
        plt.title('River network (>200 accumulation)')
        plt.xlim(self.grid.bbox[0], self.grid.bbox[2])
        plt.ylim(self.grid.bbox[1], self.grid.bbox[3])
        ax.set_aspect('equal')

        for branch in self.branches['features']:
            line = np.asarray(branch['geometry']['coordinates'])
            plt.plot(line[:, 0], line[:, 1])
        # plt.show()

    def snap_xy(self):
        xy = np.column_stack([self.x_coordinate, self.y_coordinate])
        new = self.grid.snap_to_mask(
            self.grid.acc > 500, xy, return_dist=False)
        self.snapx = new[:, 0]
        self.snapy = new[:, 1]

    def run_for_catchment(self):
        # self.init_grid()
        # self.readwindow()
        # self.conditioning()
        # self.calculate_flow_dir()
        # self.calculate_accumlation()
        # self.snap_xy()

        self.grid.catchment(x=self.snapx, y=self.snapy, data=self.output_name_dir, dirmap=self.direction_map,
                            out_name=self.output_name_catch_sub, recursionlimit=15000, xytype='label')

        self.grid.clip_to(self.output_name_catch_sub)
        fig, ax = plt.subplots(figsize=(6.5, 6.5))

        shapes = self.grid.polygonize()

        for shape in shapes:
            coords = np.asarray(shape[0]['coordinates'][0])
            ax.plot(coords[:, 0], coords[:, 1], color='k')

        ax.set_xlim(self.grid.bbox[0], self.grid.bbox[2])
        ax.set_ylim(self.grid.bbox[1], self.grid.bbox[3])
        ax.set_title('Catchment boundary (vector)')
        # plt.show()

    def to_shape(self, location_, shp=False, geojson=True):
        shapes = self.grid.polygonize()
        schema = {
            'geometry': 'LineString',
            'properties': {}
        }
        if geojson:
            fc_out = {"features": [], "type": "FeatureCollection"}
            for feature in self.branches["features"]:
                feature_out = feature.copy()
                new_coords = []
                # Project/transform coordinate pairs of each ring
                # (iteration required in case geometry type is MultiPolygon, or there are holes)
                for ring in feature["geometry"]["coordinates"]:
                    new_coords.append(
                        [c[0] for c in (transform(Proj(init='epsg:23036'), Proj(init='epsg:3857'), *zip(ring)))])
                feature_out["geometry"]["coordinates"] = new_coords
                fc_out["features"].append(feature_out)

            with open(os.path.join(location_, 'river.geojson'), 'w') as file_:
                csv_writer = csv.writer(file_, quotechar='|', delimiter='@')
                csv_writer.writerow([json.dumps(fc_out)])
                # csv_writer.writerow([self.branches['features']])
            # i = 0
            # in_projection = Proj(init='epsg:23036')
            # out_projection = Proj(init='epsg:4326')
            # last_value = 0
            # coords= [[]]
            # for shape, value in shapes:
            #     if last_value < len(shape['coordinates'][0]):
            #         coords[0] = []
            #         for index, val in enumerate(shape['coordinates'][0]):
            #             coords[0].append([transform(in_projection, out_projection, val[0], val[1])[0],
            #                               transform(in_projection, out_projection, val[0], val[1])[1]])
            #         last_value = len(shape['coordinates'][0])
            #     else:
            #         pass
            # return coords
            # with open('a.geojson', 'w') as file_:
            #     csv_writer = csv.writer(file_, quotechar='|', delimiter='@')
            #     csv_writer.writerow(['{"type": "FeatureCollection", "features":[{"type":"Feature", "properties": {}, '
            #                          '"geometry":{"type":"Polygon", "coordinates":'])
            #     csv_writer.writerow([str(coords)])
            #     csv_writer.writerow(['}}]}'])
        if shp:

            with fiona.open(os.path.join(self.process_path, "rivers.shp"), 'w',
                            driver='ESRI Shapefile',
                            crs=self.grid.crs.srs,
                            schema=schema) as c:
                i = 0
                for branch in self.branches['features']:
                    rec = {}
                    rec['geometry'] = branch['geometry']
                    rec['properties'] = {}
                    rec['id'] = str(i)
                    c.write(rec)
                    i += 1

            shapes = self.grid.polygonize()

            schema = {
                'geometry': 'Polygon',
                'properties': {'LABEL': 'float:16'}
            }

            with fiona.open(os.path.join(self.process_path, "Boundary.shp"), 'w',
                            driver='ESRI Shapefile',
                            crs=self.grid.crs.srs,
                            schema=schema) as c:
                i = 0
                for shape, value in shapes:
                    rec = {}
                    rec['geometry'] = shape
                    rec['properties'] = {'LABEL': str(value)}
                    rec['id'] = str(i)
                    c.write(rec)
                    i += 1


if __name__ == '__main__':
    start = datetime.datetime.now()
    bas = CreateCacthment(480189.932, 4100069.151)
    bas.process_path = r"D:\Github\model_experiment\NAM\file_uploads\srtm"
    bas.basin_dem = os.path.join(bas.process_path, "DEM_ED50_re.tif")
    bas.init_grid()
    bas.readwindow()
    bas.conditioning()
    # bas.resample()
    bas.calculate_flow_dir()
    bas.calculate_accumlation()
    # bas.dem_export()
    bas.snaptoacc()
    bas.snap_xy()
    bas.run_for_catchment()
    bas.to_shape()
    end = datetime.datetime.now() - start

    print(end)
