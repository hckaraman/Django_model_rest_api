import math
import numpy as np
import matplotlib.pyplot as plt
import io
import base64
import warnings
from pandas.plotting import register_matplotlib_converters
import seaborn

seaborn.set()
register_matplotlib_converters()


def muskingam_run(df, distance):
    # All Warnings Ignored !!!
    warnings.filterwarnings("ignore")
    L = distance
    # L = 21000
    # print(L)
    # Working Directory
    # os.chdir('D:\\DRIVE\\TUBITAK\\Muskingum\\Natural')
    # os.chdir(r'C:\Users\user\Documents\GitHub\NAM\datadir\scripts')

    # import pandas data frame
    # df = pd.read_csv('Darbogaz_inflow.csv', sep=',', parse_dates=[0], header=0)
    # df.index = pd.to_datetime(in_data_frame)

    # Time difference calculation
    try:
        # FutureWarning: Passing integers to fillna is deprecated, will raise a TypeError in a future version.
        # To retain the old behavior, pass pd.Timedelta(seconds=n) instead.
        df['dt'] = (df.Date - df.Date.shift()).fillna(0)
    except warnings.catch_warnings():
        print('Warning:', Warning)
    # df['dt'] =pd.to_timedelta(df['Date'],unit='s')
    df.dt = df['dt'].dt.total_seconds()

    # Number of time
    n = df.__len__()

    # Resample hourly
    # dfh = df.resample('H').mean()
    # dfh.to_csv('hourly.csv')

    # Parameters

    # L = 21000.    #   Channel Length
    # L = 20999.      # Channel Length
    dL = 1000.  # Section Length
    Llat = L / 2.  # Lateral Flow distance
    B = 4.  # Channel Width
    So = 0.001  # Channel Slope
    nman = 0.028  # Manning n
    To = B  # Top Width

    # Constants
    alfa = 0.5 * math.sqrt(So) / nman  # Constant
    m = 5 / 3.  # XS costant

    # Time = []
    # Discharge = []
    # with open('inflow_cakit.csv') as csvDataFile:
    #    csvReader = csv.reader(csvDataFile)
    #    for row in csvReader:
    #        Time.append(float(row[0]))
    #        Discharge.append(float(row[1]))
    # dt = (Time[1]-Time[0])*60
    # number = int(len(Time))

    # # of Section calc.

    SecNum = int(L / dL)
    L1 = SecNum * dL

    if L1 < L:
        SecNum = SecNum + 1
        dlfin = L - L1
    else:
        SecNum = SecNum

    Lar = [0] * (SecNum + 1)

    for i in range(SecNum):
        Lar[i + 1] = Lar[i] + dL

    Lar[SecNum] = L
    dLar = [0] * (SecNum)

    for i in range(SecNum):
        dLar[i] = Lar[i + 1] - Lar[i]

    # Lateral Flow position

    nl = int((Llat / L) * len(Lar))

    if Lar[nl] != Llat:
        if abs(Llat - Lar[nl]) > abs(Llat - Lar[nl]):
            nl = nl + 1

    # initilize Discharge

    Q = np.zeros((n, len(Lar)))
    Qmus = np.zeros((n, len(Lar)))
    Qlat = np.zeros(n)
    Qlat[:] = 0.

    # Qh = np.zeros(dfh.__len__(),len(Lar))

    # Discharce BC

    Q[:, 0] = df.Qsim[:]
    Qmus[:, 0] = df.Qsim[:]

    Q[0, :] = Q[0, 0]
    Qmus[0, :] = Q[0, 0]

    # Muskingam calculations

    k1 = 40.
    x1 = 0.2
    dt1 = 1.
    for i in range(1, n):
        for j in range(1, len(Lar)):
            C11 = (dt1 - 2 * k1 * x1) / (2 * k1 * (1 - x1) + dt1)
            C22 = (dt1 + 2 * k1 * x1) / (2 * k1 * (1 - x1) + dt1)
            C33 = (2 * k1 * (1 - x1) - dt1) / (2 * k1 * (1 - x1) + dt1)
            Q[i, j] = C11 * Q[i - 1, j] + C22 * \
                Q[i - 1, j - 1] + C33 * Q[i, j - 1]
    Qmus = Q

    # Manning's eqn fnc

    def f(x):
        return Qave - ((x * B / nman) * ((x * B / (2. * x + B)) ** (2. / 3.)) * (So ** 0.5))

    # initilize Discharge

    Q = np.zeros((n, len(Lar)))

    # Discharge BC

    Q[:, 0] = df.Qsim[:]
    Q[0, :] = Q[0, 0]

    # Muskingam - Cunge Calculations

    for i in range(1, n):

        # Discharge iterations in time

        for j in range(1, len(Lar)):

            # Average Q
            Qave = (Q[i - 1, j - 1] + Q[i, j - 1] + Q[i - 1, j]) / 3.
            Qave1 = (Q[i - 1, j - 1] + Q[i, j - 1] +
                     Q[i - 1, j] + Q[i, j]) / 4.
            ErrorQ = abs(Qave - Qave1)

            # Dishcarge iterations in space

            while ErrorQ > 0.0001:

                A = (Qave / alfa) ** (1. / m)  # Area
                u = Qave / A  # Average velocity
                A1 = Qave / To  # Constant
                A2 = So * m * u * dL  # Constant
                x = 0.5 * (1. - A1 / A2)
                K = dL / (m * u)

                # Check for Lenght constraint
                Lcont = 0.5 * (m * u * df.dt[i] + (Qave / To) / (m * u * So))
                if (Lcont < dL):
                    # print("Length condition is not valid, try smaller dL value")
                    quit()

                # Cunge constants

                Co = (-K * x + 0.5 * df.dt[i]) / \
                    (K * (1. - x) + 0.5 * df.dt[i])
                C1 = (K * x + 0.5 * df.dt[i]) / (K * (1. - x) + 0.5 * df.dt[i])
                C2 = (K * (1. - x) - 0.5 *
                      df.dt[i]) / (K * (1. - x) + 0.5 * df.dt[i])
                Q[i, j] = Co * Q[i, j - 1] + C1 * \
                    Q[i - 1, j - 1] + C2 * Q[i - 1, j]
                Qave1 = (Q[i - 1, j - 1] + Q[i, j - 1] +
                         Q[i - 1, j] + Q[i, j]) / 4.
                ErrorQ = Qave - Qave1
                if (abs(Qave - Qave1) > 0.0001):
                    Qave = Qave1

        # Add Lateral Flow

        for k in range(len(Lar)):
            if k == nl:
                Q[i, k] = Q[i, k] + Qlat[i]

        # Print iteration #
        # if i % 50 == 0:
        # print("iteration %d of %d is done\n" % (i, n))
        # plt.plot(df.Date, Q[:, 0], 'b-', df.Date, Q[:, len(dLar) - 1], 'r--', df.Date, Qmus[:, len(dLar) - 1], 'c-', )
        # plt.pause(0.3)

    def draw():
        fig = plt.figure(figsize=(15, 10))
        ax = fig.add_subplot(111)
        color = 'tab:red'
        ax.set_title('Muskingum - Cunge Routing', style='italic',
                     fontweight='bold', fontsize=16)
        ax.set_xlabel('Date', style='italic', fontweight='bold',
                      labelpad=20, fontsize=13)
        ax.set_ylabel(r'Discharge m$^3$/s', color=color, style='italic',
                      fontweight='bold', labelpad=20, fontsize=13)
        ax.tick_params(axis='y', labelcolor=color)
        ax.tick_params(axis='x', labelrotation=45)
        # ax.grid()
        plt.plot(df.Date, Q[:, 0], 'b-', df.Date,
                 Q[:, len(Lar) - 1], 'r--', linewidth=2.0)
        # plt.plot(df.Date, Q[:, 0], 'b-', df.Date, Q[:, nl], 'r--', df.Date, Qmus[:, len(dLar) - 1], 'c-', df.Date, Qlat[:],'o-')
        plt.gca().legend(('Simulated run-off', 'Simulated and routed run-off',))
        # plt.show()
        fig.tight_layout()
        tmpFile = io.BytesIO()
        plt.savefig(tmpFile, format='png')
        str = b"data:image/png;base64," + base64.b64encode(tmpFile.getvalue())
        # print(str.decode())
        # sys.stdout.flush()
        return str.decode()

    png_string = draw()

    df['Q_in'] = Q[:, 0]
    df['Qout'] = Q[:, len(Lar) - 1]

    k = df.to_json(orient='records')
    # Save results
    #
    # f = open("result.txt", "w")
    # np.savetxt('result.txt', Q)
    # np.savetxt('result.txt', Q[:, len(dLar) - 1])
    return [png_string, Q[:, len(Lar) - 1], k]
