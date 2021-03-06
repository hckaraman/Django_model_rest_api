# region modules
import numpy as np
import math
import pandas as pd
import os
import matplotlib.pyplot as plt
from scipy.optimize import minimize
import seaborn
from scipy import stats
from matplotlib.offsetbox import AnchoredText
import io
import base64
from matplotlib.gridspec import GridSpec
from . import nam_fun as nam_f
from . import objectivefunctions as objfunc
from . import config
import pathlib

mode = "run"
run_path = config.ModeSelector(mode).get_path
verbose = config.ModeSelector(mode).get_verbose



# endregion

pd.plotting.register_matplotlib_converters(explicit=True)
seaborn.set()
np.seterr(all='ignore')


class Nam(object):

    def __init__(self, area, input_parameters, calibration=False, func=None):
        self._working_directory = None
        self.Data_file = None
        self.df = None
        self.P = None
        self.T = None
        self.E = None
        self.Qobs = None
        self.area = area / (3.6 * 24)
        self.Area = area
        self.Spinoff = 100
        self.parameters = None
        self.Qfit = None
        self.dfh = None
        # self.initial = np.array([10, 100, 0.5, 500, 10, 0.5, 0.5, 0, 2000, 2.15,2])
        # self.initial = np.array([5.59441567e+00,6.85168038e+02,1.30412167e-01,8.47239393e+02,4.00934557e+01,4.21557738e-01,4.88201564e-01,4.09627612e-02,1.67517734e+03,4.09537018e-01,3.71693424e+00])
        self.initial = np.array(input_parameters)
        self.Qsim = None
        self.n = None
        self.Date = None
        self.bounds = (
            (0.01, 50), (0.01, 1000), (0.01, 1), (200, 1000), (10,
                                                               50), (0.01, 0.99), (0.01, 0.99), (0.01, 0.99),
            (500, 5000), (0, 4), (-2, 4))
        self.NSE = None
        self.RMSE = None
        self.PBIAS = None
        self.Cal = calibration
        self.statistics = None
        self.export = 'Result.csv'
        self.flowduration = None
        self.func = func

    @property
    def process_path(self):
        return self._working_directory

    @process_path.setter
    def process_path(self, value):
        self._working_directory = value
        pass

    def DataRead(self):
        self.df = pd.read_csv(self.Data_file, sep=',',
                              parse_dates=[0], header=0)
        self.df = self.df.set_index('Date')

    def InitData(self):
        self.P = self.df.P
        self.T = self.df.Temp
        self.E = self.df.E
        self.Qobs = self.df.Q
        self.n = self.df.__len__()
        self.Qsim = np.zeros(self.n)
        self.Date = self.df.index.to_pydatetime()

    def nash(self, qobserved, qsimulated):
        s, e = np.array(qobserved), np.array(qsimulated)
        # s,e=simulation,evaluation
        mean_observed = np.nanmean(e)
        # compute numerator and denominator
        numerator = np.nansum((e - s) ** 2)
        denominator = np.nansum((e - mean_observed) ** 2)
        # compute coefficient
        return 1 - (numerator / denominator)

    def Objective(self, x):
        self.Qsim = nam_f.nam_method(
            x, self.P, self.T, self.E, self.area, self.Spinoff)
        # n = math.sqrt((sum((self.Qsim - self.Qobs) ** 2)) / len(self.Qobs))

        if self.func == 'RMSE':
            n = objfunc.rmse(self.Qobs, self.Qsim)
        elif self.func == 'RMPW':
            mean_obs = np.mean(self.Qobs)
            mean_sim = np.mean(self.Qsim)
            n = np.sqrt(
                sum(((self.Qobs + mean_obs) * ((self.Qobs - self.Qsim) ** 2) / (2 * mean_obs))) / len(self.Qsim))
        elif self.func == 'R2':
            n = 1 - objfunc.rsquared(self.Qobs, self.Qsim)
        elif self.func == 'NSLF':
            mean_obs = np.mean(self.Qobs)
            mean_sim = np.mean(self.Qsim)
            A = (self.Qobs.min() - mean_obs) * (self.Qobs - mean_obs)
            B = 2 * mean_obs * (self.Qobs.max() - mean_obs)
            C = ((self.Qobs - self.Qsim) ** 2)
            D = sum((self.Qobs - mean_obs) ** 2)
            n = sum(((A / B) + 1) * C) / D
        elif self.func == 'NSHF':
            mean_obs = np.mean(self.Qobs)
            mean_sim = np.mean(self.Qsim)
            n = (sum(((self.Qobs + mean_obs) * ((self.Qobs - self.Qsim) **
                                                2) / (2 * mean_obs))) / (sum((self.Qobs - mean_obs) ** 2)))

        elif self.func == 'NSE':
            n = 1 - objfunc.nashsutcliffe(self.Qobs, self.Qsim)

        elif self.func == 'KGE':
            n = 1 - objfunc.kge(self.Qobs, self.Qsim)

        elif self.func == 'FQ':
            v = self.Qobs.min()
            mean_obs = np.mean(self.Qobs)
            mean_sim = np.mean(self.Qsim)
            A = sum((np.log(self.Qsim + v) - np.log(self.Qobs + v)) ** 2)
            B = sum((np.log(self.Qsim + v) - np.log(mean_obs + v)) ** 2)
            FlogNS = A / B

            # transformation parameter
            y = 0.3
            Qsimprime = np.divide(np.power(self.Qsim + 1, y) - 1, y)
            Qobsprime = np.divide(np.power(self.Qobs + 1, y) - 1, y)
            # Qobsprime = (((Qsim + 1) ** y) - 1) / y

            mean_obs_prime = np.mean(Qobsprime)
            FboxNS = sum((Qsimprime - Qobsprime) ** 2) / \
                     (sum((Qsimprime - mean_obs_prime) ** 2))

            r = np.corrcoef(self.Qsim, self.Qobs)[0, 1]
            Qsim_std = np.std(self.Qsim)
            Qobs_std = np.std(self.Qobs)
            X = (1 - r) ** 2
            Y = (1 - Qsim_std / Qobs_std) ** 2
            Z = (1 - mean_sim / mean_obs) ** 2
            FKGE = (X + Y + Z) ** 0.5

            Fbias = (max(self.Qsim.mean() / self.Qobs.mean(),
                         self.Qobs.mean() / self.Qsim.mean()) - 1) ** 2

            a = 5 / 7
            Fq = FlogNS + FboxNS + FKGE + Fbias
            n = Fq

        return n

    def run(self):
        self.DataRead()
        self.InitData()
        # self.func = 'FQ'
        if self.Cal:
            self.parameters = minimize(self.Objective, self.initial, method='SLSQP', bounds=self.bounds,
                                       options={'maxiter': 1e8, 'disp': False})
            self.Qsim = nam_f.nam_method(
                self.parameters.x, self.P, self.T, self.E, self.area, self.Spinoff)
            self.parameters = self.parameters.x

        else:
            self.Qsim = nam_f.nam_method(
                self.initial, self.P, self.T, self.E, self.area, self.Spinoff)
            self.parameters = self.initial

    def update(self):
        self.stats()
        fit = self.interpolation()
        self.Qfit = fit(self.Qobs)
        self.df['Qsim'] = self.Qsim
        self.df['Qfit'] = self.Qfit
        self.dfh = self.df.resample('M').mean()
        self.flowduration = pd.DataFrame()
        self.flowduration['Qsim_x'] = self.flowdur(self.Qsim)[0]
        self.flowduration['Qsim_y'] = self.flowdur(self.Qsim)[1]
        self.flowduration['Qobs_x'] = self.flowdur(self.Qobs)[0]
        self.flowduration['Qobs_y'] = self.flowdur(self.Qobs)[1]
        # self.df.to_csv(os.path.join(self.process_path, self.export), index=True, header=True)

    def stats(self):
        mean = np.mean(self.Qobs)
        # mean2 = np.mean(self.Qsim)
        self.NSE = 1 - (sum((self.Qsim - self.Qobs) ** 2) /
                        sum((self.Qobs - mean) ** 2))
        self.RMSE = np.sqrt(sum((self.Qsim - self.Qobs) ** 2) / len(self.Qsim))
        self.PBIAS = (sum(self.Qobs - self.Qsim) / sum(self.Qobs)) * 100
        self.statistics = objfunc.calculate_all_functions(self.Qobs, self.Qsim)

    def interpolation(self):
        fit = np.polyfit(self.Qobs, self.Qsim, 1)
        fit_fn = np.poly1d(fit)
        return fit_fn

    def draw(self):
        self.stats()
        fit = self.interpolation()
        self.Qfit = fit(self.Qobs)
        width = 15  # Figure width
        height = 10  # Figure height
        f = plt.figure(figsize=(width, height))
        widths = [2, 2, 2]
        heights = [2, 3, 1]
        gs = GridSpec(3, 3, figure=f, width_ratios=widths,
                      height_ratios=heights)
        ax1 = f.add_subplot(gs[1, :])
        ax2 = f.add_subplot(gs[0, :], sharex=ax1)
        ax3 = f.add_subplot(gs[-1, 0])
        ax4 = f.add_subplot(gs[-1, -1])
        ax5 = f.add_subplot(gs[-1, -2])
        color = 'tab:blue'
        ax2.set_ylabel('Precipitation ,mm ', color=color,
                       style='italic', fontweight='bold', labelpad=20, fontsize=13)
        ax2.bar(self.Date, self.df.P, color=color,
                align='center', alpha=0.6, width=1)
        ax2.tick_params(axis='y', labelcolor=color)
        # ax2.set_ylim(0, max(self.df.P) * 1.1, )
        ax2.set_ylim(max(self.df.P) * 1.1, 0)
        ax2.legend(['Precipitation'])
        color = 'tab:red'
        ax2.set_title('NAM Simulation', style='italic',
                      fontweight='bold', fontsize=16)
        ax1.set_ylabel(r'Discharge m$^3$/s', color=color,
                       style='italic', fontweight='bold', labelpad=20, fontsize=13)
        ax1.plot(self.Date, self.Qobs, 'b-', self.Date,
                 self.Qsim, 'r--', linewidth=2.0)
        ax1.tick_params(axis='y', labelcolor=color)
        ax1.tick_params(axis='x', labelrotation=45)
        ax1.set_xlabel('Date', style='italic',
                       fontweight='bold', labelpad=20, fontsize=13)
        ax1.legend(('Observed Run-off', 'Simulated Run-off'), loc=2)
        plt.setp(ax2.get_xticklabels(), visible=False)
        anchored_text = AnchoredText("NSE = %.2f\nRMSE = %0.2f\nPBIAS = %0.2f" % (self.NSE, self.RMSE, self.PBIAS),
                                     loc=1, prop=dict(size=11))
        ax1.add_artist(anchored_text)
        # plt.subplots_adjust(hspace=0.05)
        ax3.set_title('Flow Duration Curve', fontsize=11, style='italic')
        ax3.set_yscale("log")
        ax3.set_ylabel(r'Discharge m$^3$/s', style='italic',
                       fontweight='bold', labelpad=20, fontsize=9)
        ax3.set_xlabel('Percentage Exceedence (%)', style='italic',
                       fontweight='bold', labelpad=20, fontsize=9)
        exceedence, sort, low_percentile, high_percentile = self.flowdur(
            self.Qsim)
        ax3.legend(['Precipitation'])
        ax3.plot(self.flowdur(self.Qsim)[0], self.flowdur(self.Qsim)[1], 'b-', self.flowdur(self.Qobs)[0],
                 self.flowdur(self.Qobs)[1], 'r--')
        # ax3.plot(self.flowdur(self.Qobs)[0], self.flowdur(self.Qobs)[1])
        ax3.legend(('Observed', 'Simulated'),
                   loc="upper right", prop=dict(size=7))

        plt.grid(True, which="minor", ls="-")

        st = stats.linregress(self.Qobs, self.Qsim)
        # ax4.set_yscale("log")
        # ax4.set_xscale("log")
        ax4.set_title('Regression Analysis', fontsize=11, style='italic')
        ax4.set_ylabel(r'Simulated', style='italic',
                       fontweight='bold', labelpad=20, fontsize=9)
        ax4.set_xlabel('Observed', style='italic',
                       fontweight='bold', labelpad=20, fontsize=9)
        anchored_text = AnchoredText("y = %.2f\n$R^2$ = %0.2f" % (
            st[0], (st[2]) ** 2), loc=4, prop=dict(size=7))
        # ax4.plot(self.Qobs, fit(self.Qsim), '--k')
        # ax4.scatter(self.Qsim, self.Qobs)
        ax4.plot(self.Qobs, self.Qsim, 'bo', self.Qobs, self.Qfit, '--k')
        ax4.add_artist(anchored_text)

        self.update()
        self.dfh = self.df.resample('M').mean()
        Date = self.dfh.index.to_pydatetime()
        ax5.set_title('Monthly Mean', fontsize=11, style='italic')
        ax5.set_ylabel(r'Discharge m$^3$/s', color=color,
                       style='italic', fontweight='bold', labelpad=20, fontsize=9)
        # ax5.set_xlabel('Date', style='italic', fontweight='bold', labelpad=20, fontsize=9)
        ax5.tick_params(axis='y', labelcolor=color)
        ax5.tick_params(axis='x', labelrotation=45)
        # ax5.set_xlabel('Date', style='italic', fontweight='bold', labelpad=20, fontsize=9)
        ax5.legend(('Observed', 'Simulated'), loc="upper right")
        exceedence, sort, low_percentile, high_percentile = self.flowdur(
            self.Qsim)
        ax5.tick_params(axis='x', labelsize=9)
        ax5.plot(Date, self.dfh.Q, 'b-', Date,
                 self.dfh.Qsim, 'r--', linewidth=2.0)
        ax5.legend(('Observed', 'Simulated'), prop={'size': 7}, loc=1)
        # ax5.plot(dfh.Q)
        # ax5.plot(dfh.Qsim)
        # ax5.legend()
        plt.grid(True, which="minor", ls="-")

        tmpFile = io.BytesIO()

        plt.subplots_adjust(hspace=0.03)
        f.tight_layout()
        plt.show()
        plt.savefig(tmpFile, format='png')
        png_string = b"data:image/png;base64," + \
                     base64.b64encode(tmpFile.getvalue())
        return png_string

    def flowdur(self, x):
        exceedence = np.arange(1., len(np.array(x)) + 1) / len(np.array(x))
        exceedence *= 100
        sort = np.sort(x, axis=0)[::-1]
        low_percentile = np.percentile(sort, 5, axis=0)
        high_percentile = np.percentile(sort, 95, axis=0)
        return exceedence, sort, low_percentile, high_percentile

    def drawflow(self):
        f = plt.figure(figsize=(15, 10))
        ax = f.add_subplot(111)
        # fig, ax = plt.subplots(1, 1)
        ax.set_yscale("log")
        ax.set_ylabel(r'Discharge m$^3$/s', style='italic',
                      fontweight='bold', labelpad=20, fontsize=13)
        ax.set_xlabel('Percentage Exceedence (%)', style='italic',
                      fontweight='bold', labelpad=20, fontsize=13)
        exceedence, sort, low_percentile, high_percentile = self.flowdur(
            self.Qsim)
        ax.plot(self.flowdur(self.Qsim)[0], self.flowdur(self.Qsim)[1])
        ax.plot(self.flowdur(self.Qobs)[0], self.flowdur(self.Qobs)[1])
        plt.grid(True, which="minor", ls="-")
        # ax.fill_between(exceedence, low_percentile, high_percentile)
        # plt.show()
        return ax


class NamWrapper(object):
    import warnings
    warnings.filterwarnings("ignore")

    def __init__(self, area, input_data, input_parameters, calibration, func):
        self.Area = area
        self.params = input_parameters
        self.Cal = calibration
        self.input_data = input_data
        self.func = func

    def run_nam(self):
        # nam inner object
        ni = Nam(self.Area, self.params, self.Cal, self.func)
        # Relative path

        NAM_folder = pathlib.Path(
            __file__).parents[1]
        work_dir = NAM_folder / "file_uploads" / self.input_data[0]

        ni.process_path = work_dir
        ni.Data_file = os.path.join(
            work_dir, self.input_data[1])
        ni.run()
        png_str = 'at'
        ni.update()
        df_res = pd.DataFrame()
        df_res['Date'] = ni.Date
        df_res['Qsim'] = ni.Qsim
        j = ni.df.to_json(orient='records')
        k = ni.dfh.to_json(orient='records')
        ni.flowduration = ni.flowduration.replace(0, 0.01)
        flow = ni.flowduration.to_json(orient='records')
        stats = ni.statistics
        # TODO class must be defined to handle large data return metrics
        return [png_str, df_res, ni.NSE, ni.RMSE, ni.parameters, ni.Qobs, ni.Qsim, ni.T, ni.P, ni.E, j, k, flow, stats]


# Sample Run
if __name__ == '__main__':
    params = [5.59441567, 685.168038, 0.130412167, 847.239393, 40.0934557, 0.421557738, 0.488201564, 0.0409627612,
              1675.17734, 0.409537018]
    params = [5.59441567e+00, 6.85168038e+02, 1.30412167e-01, 8.47239393e+02, 4.00934557e+01, 4.21557738e-01,
              4.88201564e-01,
              4.09627612e-02, 1.67517734e+03, 4.09537018e-01, 3.71693424e+00]
    path = r"D:\Github\Django\catchment\file_uploads"
    n = NamWrapper(97.5, [path,
                          "Alihoca.csv"], params, False, func='NSE')
    a = n.run_nam()
    print(a[13])
