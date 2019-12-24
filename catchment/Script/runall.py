import sys
import io
import base64
import pandas as pd
import json
import numpy as np
from. import musk_routine
from. import sensitivity_routine
import matplotlib.pyplot as plt
import matplotlib
from . import nam
import datetime
import csv
import os


# figure Error fix
matplotlib.use('Agg')


def run_all(arg):

    st = datetime.datetime.now()

    # Read input Data
    # js = sys.argv[1]
    # Convert to python objects
    arguments = json.loads(arg)
    log_file = open('log_file_nam.csv', mode='a')
    log_writer = csv.writer(log_file, delimiter=',',
                            quotechar='"', quoting=csv.QUOTE_MINIMAL)
    # log_writer.writerow([arguments])
    # Read retrieved nam input parameters
    namParameters = [float(row)
                     for row in arguments[0]["namParameters"].split(',')]

    # Define temporary and template variables
    temp_muskingam = []
    arr = []
    nam_object = []
    musk_exit_object = []
    date_vector = 0

    # Read all the retrieved basin  information in according to the basin id
    basins = [row['basinid'] for row in arguments]

    # Two Dimensional Matrix Solution
    for en_upper, argument in enumerate(arguments):
        if argument['nam']:

            # namParameters = [1.06653896e+00, 7.85803777e-01, 1.12456396e+00, 4.00000005e-02
            #     , 6.52779758e+01, 1.40000000e+00, 2.04563613e-01, 5.00000000e-01
            #     , 7.23806920e-03, 6.20000000e-04, 5.98308241e-01, 2.29012429e+00
            #     , 2.32816764e-02, 4.01249854e-01, 0.00000000e+00, 1.25000000e-01
            #                 , 1.19040117e+00,1.40000000e+00,6.15462361e+00]

            nm_result = nam.NamWrapper(float(argument['area']),
                                       argument['meteorologyfile'],
                                       input_parameters=namParameters,
                                       calibration=argument['calibration'], func='NSE').run_nam()

            arr.append(nm_result[1].Qsim.values)
            date_vector = pd.to_datetime(nm_result[5].index)
            csv_content = np.vstack([
                # Date
                np.datetime_as_string(nm_result[5].index)            # Q Observed
                , nm_result[5].values            # Q simulated
                , nm_result[1].Qsim.values            # Temperature
                , nm_result[7].values, nm_result[8].values  # P
                , nm_result[9].values  # E
            ]).transpose().tolist()
            csv_content = [['Date', 'Qobs', 'Qsim', 'Temperature',
                            'Precipitation', 'Evapotranspiration']] + csv_content
            nam_object.append({f"id": f"{argument['basinid']}",
                               "image": nm_result[0],
                               "downloads": json.dumps(csv_content),
                               "nse": nm_result[2],
                               "rmse": nm_result[3],
                               "parameters": json.dumps(nm_result[4].tolist()),
                               "data": nm_result[10],
                               "datah": nm_result[11],
                               'flow': nm_result[12],
                               'stats': nm_result[13]})
        if argument['muskingam']:
            for en_inner, elinner in enumerate(arguments):
                dis = float(argument['distance']) - \
                    float(arguments[en_inner]['distance'])
                if en_inner == en_upper:
                    arr.append(nm_result[1].Qsim.values)
                elif en_inner > en_upper:
                    b = musk_routine.muskingam_run(nm_result[1], dis)
                    arr.append(b[1])
                else:
                    arr.append(0)
            b = musk_routine.muskingam_run(nm_result[1], argument['distance'])
            arr.append(b[1])
            musk_exit_object.append({"id": argument['basinid'], "image": ''})
        elif argument['muskingam'] is False:
            for _ in range(len(arguments) + 1):
                arr.append(0)
        if argument['sensitivity'] is True:
            c = sensitivity_routine.sensitivity_run(
                float(argument['area']), argument['meteorologyfile'], nm_result[-1])
            arr.append(c)
        elif argument['sensitivity'] is False:
            arr.append(0)
        arr.append(nm_result[0])
    # endregion

    two_dimensional_matrix = np.array(arr).reshape(en_upper + 1, en_upper + 5)
    filtered_2d_matrix = np.sum(two_dimensional_matrix[:, 0:-2], axis=0)
    filtered_2d_matrix = np.concatenate((filtered_2d_matrix, [0], [0]))
    two_dimensional_matrix = np.vstack(
        [two_dimensional_matrix, filtered_2d_matrix])

    i = 0
    return_json_object = []
    musking_object = []
    sens_object = []

    node_id = 1001
    catchment_id = 0
    width = 15  # Figure width
    height = 10  # Figure height
    color = 'tab:red'  # Figure Font Color
    for i in range(two_dimensional_matrix.shape[1] - 2):
        if i > 0:
            if i == two_dimensional_matrix.shape[1] - 3:
                node_id = 1000
            x = two_dimensional_matrix[:, i:i + 1]
            f = plt.figure(i + 99, figsize=(width, height))
            basin_nr = 1001
            print(i,basin_nr)
            data = []
            for argument in x:
                if hasattr(argument[0], "__len__"):
                    # print(el[0].__len__())
                    # plt.plot(date_vector, argument[0])
                    data.append(argument[0])
                else:
                    # plt.plot(date_vector, np.zeros(len(date_vector)))
                    data.append(np.zeros(len(date_vector)))
                # TODO Basin ID will be fixed
                if node_id == 1000:
                    plt.title(f'Outlet Result')
                else:
                    plt.title(f'Basin {node_id}  Routing Results')
                basin_nr += 1
            f.legend([("Basin" + str(row['basinid']))
                      for row in arguments] + ["Total"])
            f.gca().set_ylabel(r'Discharge m$^3$/s', color=color, style='italic', fontweight='bold', labelpad=20,
                               fontsize=13)
            f.gca().set_xlabel('Date', style='italic',
                               fontweight='bold', labelpad=20, fontsize=13)
            # f.tick_params(axis='y', labelcolor=color)
            # f.tick_params(axis='x', labelrotation=45)
            # tmpFile = io.BytesIO()
            # plt.savefig(tmpFile, format='png')
            # png_string = b"data:image/png;base64," + \
            #     base64.b64encode(tmpFile.getvalue())
            # log_writer.writerow([np.datetime_as_string(data)])
            df_res = pd.DataFrame()
            # df_res['Date'] = nm_result[5].index.values
            df_res['Qsim'] = data
            j = df_res.to_json(orient='records')
            if i == two_dimensional_matrix.shape[1] - 3:

                musking_object.append(
                    {f"id": f"{1000}", "image":  j})
            else:
                musking_object.append(
                    {f"id": f"{basins[catchment_id]}", "image":  j})
            node_id += 1
            catchment_id += 1
    # endregion
    # region Appending Sensitivity Results to Object
    basin_nr = 1001

    # print( "4", datetime.datetime.now() - st )

    for sens_img in two_dimensional_matrix[:, two_dimensional_matrix.shape[0] + 1:two_dimensional_matrix.shape[0] + 2]:
        try:
            sens_object.append({"id": basin_nr, "image": ''})
        except BaseException as be:
            sens_object.append({"id": basin_nr, "image": ''})
        basin_nr += 1
    # endregion

    return_json_object = {
        'result': [{'nam_result_nodes': nam_object}, {'musk_result': musking_object}, {'sens_result': sens_object},
                   {'musk_exit': musk_exit_object}]}
    # return_json_object = json.dumps(return_json_object)
    return (return_json_object)
