import os
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from. import nam_fun as nam_f
import io
import base64
from. import config

pd.plotting.register_matplotlib_converters()


def sensitivity_run(area, met_data, calibration_parameters):
    # Working Directory
    global png_string

    # Area = 97.65  # Basin Area
    # Area = float(sys.argv[1])
    Area = area
    SpinOff = 0  # Spinoff Time
    MaxT = 722  # Time Step
    c = []
    area = Area / (3.6 * 24)

    # import pandas data frame
    df = pd.read_csv(os.path.join(config.local_path, 'meteorology_data',
                                  met_data), sep=',', parse_dates=[0], header=0)
    df.index = pd.to_datetime(df['Date'])

    # Parameter bounds
    lower = np.array([0, 0, 0, 200, 10, 0.0, 0.0, 0.0, 500, 2])
    upper = np.array([50, 1000, 1, 1000, 50, 0.99, 0.99, 0.99, 5000, 4])

    # Set initial guess
    # initial = lower + rnorm(length(lower), sd = 0.3)
    initial = np.array(calibration_parameters)

    # np.array([1.0000, 1000.0000, 0.4423, 416.6595, 10.0000, 0.8451, 0.0000, 0.1392, 1399.5852, 2.9316])

    # Sensitivity parameters
    param = ['Umax ', 'Lmax', 'CQOF', 'CKIF',
             'CK12', 'TOF', 'TIF', 'TG', 'CKBF', 'Csnow']

    # Define variables
    par = 1.0
    P = df.P * par
    T = df.Temp
    E = df.E
    Qobs = df.Q

    # Observed discharge + spinoff
    Qobs = Qobs[SpinOff:]
    Qsim = np.zeros((len(Qobs)))

    # Parameter bounds
    b = [1, 50, 1, 1000, 0, 1, 200, 1000, 10, 50,
         0, 0.99, 0, 0.99, 0, 0.99, 500, 5000, 0, 4]

    # Plot initilization

    width = 15  # Figure width
    height = 10  # Figure height

    f, axarr = plt.subplots(5, 2)
    f.set_size_inches(width, height)
    f.suptitle('Nash–Sutcliffe Model Efficiency Coefficient (NSE)',
               fontsize=14, fontweight='bold', style='italic')
    plt.subplots_adjust(left=None, bottom=0.1, right=None,
                        top=0.9, wspace=None, hspace=0.75)

    f1, axarr1 = plt.subplots(5, 2)
    f1.set_size_inches(width, height)
    f1.suptitle('Root Mean Square Error (RMSE)', fontsize=14,
                fontweight='bold', style='italic')
    plt.subplots_adjust(left=None, bottom=0.1, right=None,
                        top=0.9, wspace=None, hspace=0.75)

    f2, axarr2 = plt.subplots(5, 2)
    f2.set_size_inches(width, height)
    f2.suptitle('Percent BIAS', fontsize=14, fontweight='bold', style='italic')
    plt.subplots_adjust(left=None, bottom=0.1, right=None,
                        top=0.9, wspace=None, hspace=0.75)

    f3, axarr3 = plt.subplots(5, 2)
    f3.set_size_inches(width, height)
    f3.suptitle(
        r'Coefficient of Determination ($\mathregular{R^2}$)', fontsize=14, fontweight='bold', style='italic')
    plt.subplots_adjust(left=None, bottom=0.1, right=None,
                        top=0.9, wspace=None, hspace=0.75)

    # todo add R2!

    # Counters

    l = 0
    l1 = 0
    l2 = 0

    # boundaries for axis stretching

    upper = 1.
    lower = 0.

    # Number of section

    sec = 25

    # initilize parameters

    RMSE = np.zeros(sec)
    NSE = np.zeros(sec)
    PBIAS = np.zeros(sec)
    cor = np.zeros(sec)
    R2 = np.zeros(sec)
    st = np.zeros(sec)
    st1 = np.zeros(sec)
    st2 = np.zeros(sec)
    st3 = np.zeros(sec)

    # Iteration in parameters
    # print('Sensitivity analysis started')
    for k in range(0, len(b), 2):
        um = np.linspace(b[k], b[k + 1], sec)

        j = 0

        # Iteration in each parameters

        for uu in um:
            # initial = np.array([1.0000,1000.0000,0.4423,416.6595,10.0000,0.8451,0.0000,0.1392,1399.5852,2.9316])
            # initial = np.array([2.7429, 4.4535, 0.0000, 539.3511, 21.9657, 0.0053, 0.8088, 0.9900, 1468.6380, 3.3370])
            initial[l] = uu
            # print(initial)

            # Calling NAM
            nam_f.nam_method(initial, P, T, E, area, Qsim, SpinOff)

            # Spinoff Date
            Date_fic = df.Date[SpinOff:]

            # Calculate Nash–Sutcliffe model efficiency coefficient
            mean = np.mean(Qobs)
            mean2 = np.mean(Qsim)
            NSE[j] = 1 - (sum((Qsim - Qobs) ** 2) / sum((Qobs - mean) ** 2))
            # print("Nash–Sutcliffe model efficiency coefficient (NSE) = %f" %NSE[j])

            # Root Mean Square Error

            RMSE[j] = np.sqrt(sum((Qsim - Qobs) ** 2) / len(Qsim))
            # print("Root Mean Square Error (RMSE) = %f" %RMSE[j])

            # Percent BIAS
            PBIAS[j] = (sum(Qobs - Qsim) / sum(Qobs)) * 100
            # print("Percent Bias (PBIAS) = %f" % PBIAS[j])

            # Pearson Coorelation coefficient squared (Coefficient of Determination)
            cor[j] = (np.corrcoef(Qsim, Qobs)[0, 1]) ** 2

            j += 1

        # Cumulative Sum
        Qobs_cum = Qobs.cumsum()
        Qsim_cum = Qsim.cumsum()

        # y-axis stretch
        for i in range(len(NSE)):
            st[i] = (NSE[i] - min(NSE)) * ((upper - lower) /
                                           ((max(NSE) - min(NSE)) + 1e-5)) + lower
            st1[i] = (RMSE[i] - min(RMSE)) * ((upper - lower) /
                                              ((max(RMSE) - min(RMSE)) + 1e-5)) + lower
            st2[i] = (PBIAS[i] - min(PBIAS)) * ((upper - lower) /
                                                ((max(PBIAS) - min(PBIAS)) + 1e-5)) + lower
            st3[i] = (cor[i] - min(cor)) * ((upper - lower) /
                                            ((max(cor) - min(cor)) + 1e-5)) + lower

        # Subplot arrangement

        if l <= 4:
            axarr[l1, 0].plot(um, st, color='blue', marker='+', ls='-')
            axarr1[l1, 0].plot(um, st1, color='blue', marker='+', ls='-')
            axarr2[l1, 0].plot(um, st2, color='blue', marker='+', ls='-')
            axarr3[l1, 0].plot(um, st3, color='blue', marker='+', ls='-')
            axarr[l1, 0].set_title(param[l])
            axarr1[l1, 0].set_title(param[l])
            axarr2[l1, 0].set_title(param[l])
            axarr3[l1, 0].set_title(param[l])
            axarr[l1, 0].grid(True, linestyle='dotted')
            axarr1[l1, 0].grid(True, linestyle='dotted')
            axarr2[l1, 0].grid(True, linestyle='dotted')
            axarr3[l1, 0].grid(True, linestyle='dotted')
            plt.grid(True)
            l1 += 1
        else:
            axarr[l2, 1].plot(um, st, color='blue', marker='+', ls='-')
            axarr1[l2, 1].plot(um, st1, color='blue', marker='+', ls='-')
            axarr2[l2, 1].plot(um, st2, color='blue', marker='+', ls='-')
            axarr3[l2, 1].plot(um, st3, color='blue', marker='+', ls='-')
            axarr[l2, 1].set_title(param[l])
            axarr1[l2, 1].set_title(param[l])
            axarr2[l2, 1].set_title(param[l])
            axarr3[l2, 1].set_title(param[l])
            axarr[l2, 1].grid(True, linestyle='dotted')
            axarr1[l2, 1].grid(True, linestyle='dotted')
            axarr2[l2, 1].grid(True, linestyle='dotted')
            axarr3[l2, 1].grid(True, linestyle='dotted')
            l2 += 1
        # print(param[l], 'done')

        l += 1

    # print('Sensitivity analysis finished')

    # Plotting
    # mng = plt.get_current_fig_manager()
    # mng.resize(*mng.window.maxsize())
    figures = [f, f1, f2, f3]

    for figure in figures:
        tmp_file = io.BytesIO()
        figure.savefig(tmp_file, format='png')
        b64bytes = base64.b64encode(tmp_file.getvalue())
        b64bytes = b64bytes.decode()
        png_string = "data:image/png;base64," + b64bytes
        # figures_json.append(json_obj)
    return (png_string)
