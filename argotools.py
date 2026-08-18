"""
Module for argo_regression_modeling.ipynb
GO-BGC Data Workshop 2026, ML Tutorial

The benefit of this modular approach is that you can access useful functions 
across different notebooks and avoid copy/pasting large sections of code. 
As your modules grow in complexity and number, you can also reformat into a 
[Python package](https://packaging.python.org/en/latest/tutorials/packaging-projects/) 
to install within an environment.

----
Code adapted from DOI:10.1175/AIES-D-24-0048.1
sangsong@uw.edu
"""

import pandas as pd
import xarray as xr
import numpy as np
from scipy import stats
import gsw

from sklearn import preprocessing
from sklearn import metrics
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestRegressor
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.model_selection import KFold
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
from sklearn.metrics import r2_score

import matplotlib.pyplot as plt
import matplotlib.colors as mpcolors
from cmocean import cm as cmo
from cartopy import crs as ccrs
from cartopy import feature as cfeature   


########################################################

# %% ML data container - store training/validation data

class CrossValContainer:
    """ Data container for cross-validation folds. 
    Stores training and validation indices for each fold, rather than subcopies of the full dataframe
    Access subsets of the input data using .loc[]
    """
    def __init__(self, input_data, nfolds):
        """ 
        :param input_data: pandas dataframe to be split into folds
        :param nfolds: integer number of splits
        """
        fold_list = ['fold' + str(k) for k in range(1, nfolds+1)]
        self.fold_list = fold_list
        self.input_data = input_data
        self.training_inds = {fold:None for fold in fold_list}
        self.validation_inds = {fold: None for fold in fold_list}

    def to_labeled_dataframe(self):
        """ Collapse training and validation data across folds into a single dataframe """
        fullDF = pd.DataFrame()
        for nfold in self.fold_list:
            temp = self.validation_data[nfold]
            temp['fold'] = np.tile(nfold, len(temp))
            fullDF = pd.concat([fullDF, temp], axis=0)

        return fullDF
    
    def populate_folds(self, subset_kwargs):
        """ See .subset_folds() for options"""
        [self.training_inds, self.validation_inds] = subset_folds(self.input_data, 
                                                                  nfolds=len(self.fold_list),
                                                                  **subset_kwargs)
        return self

    def map_folds(self, axs=None, figsize=(12,6), ax_lims = [-127, -121, 34, 38], glider_data=None, show_legend=True):
        """ Map the training and validation data for each fold in a paneled plot.
        Modified to automatically plot CCE region for this workshop.
        :param axs: optional array of axes to plot on, if None will create new figure
        :param ax_lims: list of [lon_min, lon_max, lat_min, lat_max] to set map extent
        :param glider_data: optional dataframe of glider data to plot on the map
        """
        plot_data = self.input_data.copy()
        nfolds = len(self.fold_list)

        if axs is None:
            fig, axs = plt.subplots(1,nfolds, figsize=figsize, layout='constrained', subplot_kw={'projection': ccrs.PlateCarree()})
        
        for ind, foldtag in enumerate(self.fold_list): 
            ax = axs[ind]
            val_data = plot_data.loc[self.validation_inds[foldtag], :].copy()
            train_data = plot_data.loc[self.training_inds[foldtag], :].copy()

            map_study_region(ax, ax_lims=ax_lims, gridlabel=False)
            ax.scatter(train_data.longitude, train_data.latitude, c='lightgrey', s=1, zorder=3,
                    transform=ccrs.PlateCarree(), label='train')
            ax.scatter(val_data.longitude, val_data.latitude, c='r', s=4, zorder=5,
                    transform=ccrs.PlateCarree(), label='val')
            
            if glider_data is not None:
                ax.scatter(glider_data.longitude, glider_data.latitude, c='navy', s=4, zorder=5,
                        transform=ccrs.PlateCarree())
        if show_legend:
            ax.legend(loc='lower right', fontsize=10, markerscale=2, framealpha=1)
        
        return fig, axs


def subset_folds(platDF, type= 'platform', indexer='wmoid', nfolds=5,
                            latitude_scaler=1 ) -> list[dict[str, pd.DataFrame]]:
    """ 
    Returns dictionary of training and validation dataframes for each fold.

    :param platDF: dataframe for either floatDF or shipDF
    :param type: options by 'platform', 'kmeans', or 'random' 
    :param indexer: choose whether to split by 'wmoid' (float) or 'profid' (profile)
                    only used if type = 'platform'
    :param nfolds: (int) number of folds for cross-validation
    :param latitude_scaler: float, scaling ratio for latitude/longitude in k-means
                            default of 1 gives range [-1.1] to match sinusoidal longitude range [-1,1]
                            changing to >1 gives more weight to latitude in clustering (ex: 3 yields range [-3,3])
    :return: training_inds: dictionary with keys 'fold1', 'fold2', ... with training DF integer locs
             validation_inds: dictionary with keys 'fold1', 'fold2', ... with validation DF integer locs

    """
    training_inds = {('fold'+str(k+1)):None for k in range(nfolds)}
    validation_inds = {('fold'+str(k+1)):None for k in range(nfolds)}
    
    if type == 'random': # not recommended!
        kf = KFold(n_splits=nfolds, random_state=42, shuffle=True)
        for ind, (train_index, val_index) in enumerate(kf.split(platDF)):
            #returns integer locs
            training_inds['fold' + str(ind+1)] = np.isin(np.arange(len(platDF)), train_index)
            validation_inds['fold' + str(ind+1)] = np.isin(np.arange(len(platDF)), val_index)

    elif type == 'platform': 
        platDF[indexer] = platDF[indexer].astype(str) #catch
        ids = platDF[indexer].unique().to_numpy()
        np.random.shuffle(ids)
        holdout_ids = np.array_split(ids, nfolds)
        for k in range(nfolds):
            training_inds[('fold'+str(k+1))] = ~platDF[indexer].isin(holdout_ids[k])
            validation_inds[('fold'+str(k+1))] = platDF[indexer].isin(holdout_ids[k])

    elif type == 'kmeans': 
        kmeans = KMeans(n_clusters=nfolds, random_state=42)
        platDF['sin_longitude'] = np.sin(np.radians(platDF['longitude']))
        platDF['cos_longitude'] = np.cos(np.radians(platDF['longitude']))

        latitude_0to1 = (platDF['latitude'] - platDF['latitude'].min()) / platDF['latitude'].max() #range 0 to 1
        platDF['scaled_latitude'] = -latitude_scaler + latitude_scaler*2*(latitude_0to1) 
        platDF['fold'] = kmeans.fit_predict(platDF[['scaled_latitude', 'sin_longitude', 'cos_longitude']])

        for fnum in range(nfolds):
            training_inds['fold' + str(fnum+1)] = platDF['fold'] != fnum
            validation_inds['fold' + str(fnum+1)] = platDF['fold'] == fnum

    return training_inds, validation_inds

########################################################
########################################################
# %% ML model container - store errors from k-fold
class CrossValModelRun:
    """ Model container / instance of a trained model with results stored by fold
    """
    def __init__(self, fold_list, description=''):
        """ Initialize container.
        
        models: sklearn objects
        validation_errors: pandas dataframe of validation errors for each fold
        calibratedDF: pandas dataframe of collapsed errors after linear calibration
        cal_coeffs: list of linear calibration coefficients [slope, intercept]
        """
        self.fold_list = fold_list
        self.models = {fold: None for fold in fold_list}
        self.validation_errors = {fold: None for fold in fold_list}
        # self.description = description # optional string tag
        self.calibratedDF = None 
        self.cal_coeffs = None

    def collapse_errors(self):
        """ Collapse validation errors across folds into a single dataframe """
        cv_errors = pd.concat([self.validation_errors[fold] for fold in self.fold_list], axis=0)
        return cv_errors
    
    def average_profiles(self, calibrated=True):
        """ Returns average error for each profile, either calibrated or uncalibrated,
        for mapping (since profiles have data at multiple depths)"""
        if calibrated: 
            result = self.calibratedDF.copy() #calibrated
            subcols = ['latitude', 'longitude', 'lincal_error', 'profid']
        else:
            result = self.collapse_errors().copy() #uncalibrated
            subcols = ['latitude','longitude', 'val_error', 'profid']
        
        return result[subcols].groupby('profid').mean()

def fit_cv_model(use_cvtainer, target_variable, use_feats, use_algorithm='RFR', use_hyperparams={}):
    """
    Main method for fitting CV run. 
    Returns CrossValModelRun object with models and validation errors stored by fold.
    
    :param use_cvtainer: CrossValContainer object with training/validation folds
    :param target_variable: string name of target variable to predict
    :param use_feats: list of feature names to use for prediction
    :param use_algorithm: string name of algorithm to use, default is 'RFR' (Random Forest Regressor)
    :param use_hyperparams: dictionary of hyperparameters for the chosen algorithm
    :return: CrossValModelRun object with models and validation errors stored by fold
    """
    print('Fitting ' + use_algorithm + '...')
    modRun = CrossValModelRun(fold_list = use_cvtainer.fold_list)

    # Populate cvtainer fields with validation errors, models for each fold 
    for nfold in use_cvtainer.fold_list:   
        trainDF = use_cvtainer.input_data.loc[use_cvtainer.training_inds[nfold]]
        valDF = use_cvtainer.input_data.loc[use_cvtainer.validation_inds[nfold]]

        modRun.models[nfold], modRun.validation_errors[nfold] = fit_single_regressor(
                                    trainDF, valDF,
                                    var_predict = target_variable, 
                                    feat_list = use_feats, # feature list
                                    regressor_type = use_algorithm,
                                    hyperparams = use_hyperparams)
        
    
    modRun.calibratedDF, modRun.cal_coeffs = apply_linear_calibration(modRun.collapse_errors(), target_variable)

    return modRun

def fit_single_regressor(
              trainingDF, validationDF,
              var_predict, 
              feat_list,
              regressor_type = 'RFR', 
              hyperparams = {'n_estimators': 100}):
    """ 
    Fit single regressor using an al, return validation errors

    :param trainingDF: pandas dataframe of training data
    :param validationDF: pandas dataframe of validation data
                        if None, return trained model without errors (for final model training)
    :param var_predict: string name of target variable to predict
    :param feat_list: list of feature names to use for prediction
    :param regressor_type: string name of algorithm to use, default 'RFR' for Random Forest
    :param hyperparams: dictionary of hyperparameters for the chosen algorithm

    :return Mdl: trained sklearn model object 
                optionally returns validation errors dataframe if validationDF is not None
    """
            
    if regressor_type == 'RFR':
        Mdl = RandomForestRegressor(**hyperparams,
                                    bootstrap=True)
    # elif regressor_type == '': # Add other regressors here

    # Train the model 
    X_training = trainingDF.dropna(subset=feat_list)[feat_list].to_numpy()
    Y_training = trainingDF.dropna(subset=feat_list)[var_predict].to_numpy().flatten()
    Mdl.fit(X_training, Y_training)

    if validationDF is not None:
        # Apply and get fold validation errors 
        resultDF = validationDF.copy()
        resultDF['val_prediction'] = Mdl.predict(validationDF[feat_list].to_numpy())
        resultDF['val_error'] = resultDF['val_prediction'] - resultDF[var_predict].to_numpy().flatten()
        resultDF['val_relative_error'] = resultDF['val_error'] / resultDF[var_predict].to_numpy().flatten()
        return Mdl, resultDF
    
    else: return Mdl

def fit_test_final_model(trainingDF, testDF,  
             var_predict, 
              feat_list,
              regressor_type = 'RFR', #regressor
              hyperparams = {'n_estimators': 100}):
    """
    Wrapper function for fitting final model and applying linear calibration 
    before computing test errors.

    :param trainingDF: pandas dataframe of training data
    :param testDF: pandas dataframe of test data
    :param var_predict: string name of target variable to predict
    :param feat_list: list of feature names to use for prediction
    :param regressor_type: string name of algorithm to use, default 'RFR' for Random Forest
    :param hyperparams: dictionary of hyperparameters for the chosen algorithm
    """
    finalMdl, test_errors = fit_single_regressor(trainingDF, 
                                testDF,
                                var_predict,
                                feat_list,
                                regressor_type,
                                hyperparams)
    
    calibrated_test_errors, cal_coeffs = apply_linear_calibration(test_errors, var_predict)
    calibrated_test_errors.rename(columns={'val_prediction':'test_prediction', 
                                'val_error':'test_error', 
                                'val_relative_error':'test_relative_error'}, inplace=True)
    return finalMdl, calibrated_test_errors, cal_coeffs

def apply_final_model(applicationDF, feat_list, finalMdl, cal_coeffs):
    """ Wrapper function to apply final model and linear calibration to new data."""
    applicationDF = applicationDF.copy()
    applicationDF['uncal_prediction'] = finalMdl.predict(applicationDF[feat_list].to_numpy())
    applicationDF['prediction'] = applicationDF['uncal_prediction'] * cal_coeffs[0] + cal_coeffs[1]
    return applicationDF

def apply_linear_calibration(valDF, target_variable):
    """ Apply linear calibration to estimates based on decile means.
    :param valDF: pandas dataframe of validation errors
    :param target_variable: string name of target variable to predict
    
    :return calibratedDF: original DF with errors added ('lincal_error')"""
    calibratedDF = valDF.copy()
    calibratedDF['n_decile'] = pd.qcut(calibratedDF['val_prediction'].values, 10, labels=list(range(1, 11))) #
    cal_pred = calibratedDF.groupby('n_decile', observed=True)['val_prediction'].agg(['mean', 'min', 'max', 'count'])
    cal_obs = calibratedDF.groupby('n_decile', observed=True)[target_variable].agg(['mean', 'min', 'max', 'count'])

    stat_var = 'mean'
    lincal = stats.linregress(cal_pred[stat_var].values, cal_obs[stat_var].values)
    calibratedDF['lincal_prediction'] = calibratedDF['val_prediction'] * lincal.slope + lincal.intercept
    calibratedDF['lincal_error'] = calibratedDF['lincal_prediction'] - calibratedDF[target_variable]
    calibratedDF['lincal_relative_error'] = calibratedDF['lincal_error'] / calibratedDF[target_variable]

    return calibratedDF,  [lincal.slope, lincal.intercept]

def summarize_errors(platDF, error_param = 'val_error', pd_format=False):
        """ 
        Summarize the chosen error metric with median absolute error, 
        mean absolute error, bias, and RMSE.

        :param platDF: pandas dataframe 
        :param error_param: string name of error column to summarize
        :param pd_format: boolean, if True returns results as a pandas dataframe, 
                        if False returns as a list, e.g. for storedRuns_comparison()
        
        """
        platDF = platDF.copy() #self.collapse_errors()

        err = platDF[error_param]
        median_abs_error = np.abs(err).median()
        mean_abs_error = np.abs(err).mean()
        bias = (err.mean())

        platDF[error_param + '_sq'] = platDF[error_param]**2
        mse = np.sum(platDF[error_param + '_sq']) / len(platDF[error_param])
        rmse = np.sqrt(mse)

        result = [median_abs_error, mean_abs_error, bias, rmse]
        if pd_format:
            result = pd.DataFrame(index=[''], data={'median_abs_error': [median_abs_error], 
                                                    'mean_abs_error': [mean_abs_error],
                                                    'bias': [bias], 'rmse': [rmse]})
        return result

    
def storedRuns_comparison(storedRuns_dict, run_tags = None, error_param='val_error', 
                          target_var='nitrate',
                          by_fold = False,
                          show=True): 
    """ 
    :param storedRuns_dict: dictionary of ModelVersion objects, runtag as keys
    :param run_tags: list of run_tags to compare, if None will run all in storedRuns
    :param by_fold: boolean, set True if storedRuns are still separated by fold
                            will first collapse errors before comparison
    :param show: boolean, if True will print the results 
    """
    #  Collapse folds into a single Dataframe for each run tag
    if run_tags is None: run_tags = [x for x in storedRuns_dict.keys()] # run all 
    
    if by_fold == True:
        storedRuns = {rkey: None for rkey in run_tags}
        for k,v in storedRuns_dict.items(): 
            storedRuns[k] = v.collapse_errors()
    else: 
        storedRuns = storedRuns_dict.copy()
        resultDF = pd.DataFrame()

    for run_tag in run_tags[:]:
        errorDF = storedRuns[run_tag].calibratedDF
        # print('==> Results for ' + run_tag)
        # print('\t features ', feat_options[run_tag.split('-')[0]])
        [run_median_abs_error, run_mean_abs_error, run_bias, run_rmse] = summarize_errors(errorDF, error_param=error_param)

        resultDF.loc[run_tag, 'median_AE'] = run_median_abs_error
        resultDF.loc[run_tag, 'mean_AE'] = run_mean_abs_error
        resultDF.loc[run_tag, 'bias'] = run_bias
        resultDF.loc[run_tag, 'RMSE'] = run_rmse

    if show: print(resultDF)
    return resultDF


########################################################
########################################################
# %% Plotting functions

def map_study_region(ax = None, ax_lims = [-127, -121, 34, 38], gridlabel=False, figsize=(8,4)):
    """ 
    Mapping shortcut for demo study region. Change default ax_lims as needed.
    :param gridlabel: boolean, if True will label gridlines with lat/lon"""
    if ax is None: 
        fig = plt.figure(figsize=figsize, layout='tight')
        ax = fig.add_subplot(1,1,1, projection=ccrs.PlateCarree())

    ax.set_extent(ax_lims)
    ax.coastlines(resolution = "50m", zorder=5, linewidth = 1)
    ax.add_feature(cfeature.LAND, zorder=5, linewidth = 1, edgecolor='k', facecolor='linen')
    ax.set_aspect('equal')
    ax.gridlines(draw_labels=gridlabel)
    
    return ax 

def plot_decile_calibration(target_estimates, target_observations, stat_var='mean', axlims = [-65, 15]):
    """ Plot decile means for linear calibration of model estimates vs. observations.
    """
    fig = plt.figure(figsize=(5,5), layout='constrained')
    ax = fig.gca()

    plot_data = pd.DataFrame({'pred': target_estimates, 'obs': target_observations})

    ax.scatter(plot_data.pred, plot_data['obs'], alpha=0.1, s=2, color='grey')
    ax.set_aspect('equal')
    plot_data['n_decile'] = pd.qcut(plot_data['pred'].values.tolist(), 10, labels=list(range(1, 11))) #
    cal_pred = plot_data.groupby('n_decile', observed=False)['pred'].agg(['mean', 'min', 'max', 'count'])
    cal_obs = plot_data.groupby('n_decile', observed=False)['obs'].agg(['mean', 'min', 'max', 'count'])

    ax.set_aspect('equal')
    ax.scatter(cal_pred[stat_var].values, cal_obs[stat_var].values, color='k', s=30) #, label='decile means')
    ax.plot([-1000,1000], [-1000,1000], color='black', linestyle='--', alpha=0.5, zorder=1)
    ax.grid(True, linestyle='--', alpha=0.5, zorder=0)

    # axlims = [-65, 15]
    ax.vlines(x=0, ymin=axlims[0], ymax=axlims[1], colors='gray', linestyles='-', alpha=0.5)
    ax.hlines(y=0, xmin=axlims[0], xmax=axlims[1], colors='gray', linestyles='-', alpha=0.5)
    ax.set_xlim(axlims); ax.set_ylim(axlims)
    ax.set_xlabel('Estimated'); ax.set_ylabel('Observed')
    lincal = stats.linregress(cal_pred[stat_var].values, cal_obs[stat_var].values)

    # Plot the fitted line using plt.axline
    ax.axline(xy1=(0, lincal.intercept), slope=lincal.slope, color='r', 
            label=f'y={lincal.slope:.2f}x+{lincal.intercept:.2f}')
    ax.legend()

    return ax 

def overlay_distributions(dataframe1, dataframe2, axs=None, 
                          axvars = ['CT', 'SA'], axunits=['[°C]', '[g/kg]'],
                          hist_kwargs={},
                          labels=[]):
    """ Overlay histograms from two datasets (e.g. two platforms) for comparison, 
     paneled by tracer variable. 
    
     :param hist_kwargs: dictionary of keyword arguments to pass to plt.hist() for customization
     :param labels: legend labels for the two datasets, e.g. ['float', 'glider']
    """
    if axs is None:
        fig, axs = plt.subplots(len(axvars),1, figsize=(6,8), layout='tight')
    
    for ind, ax in enumerate(axs.flatten()):
        ax.hist(dataframe1[axvars[ind]], rwidth=1, facecolor='navy', alpha=0.8, density=True, zorder=3)
        ax.hist(dataframe2[axvars[ind]], rwidth=1, facecolor='orange', alpha=0.7, density=True, zorder=3)
        ax.set_title(axvars[ind] + ' ' + axunits[ind])
        ax.grid(alpha=0.5, zorder=1)
        ax.set_ylabel('density')
    ax.legend(labels, loc='upper right', fontsize=10, framealpha=1)
    
    return axs


def get_depth_bias(data, ranges, var='val_error'):
    """ Get validation errors in 100m depth bins. 
    Use with boxplot_depth_binned() to visualize errors by depth."""
    # Example range to pass as @param: ranges
    # pressure_ranges = [(0, 100), (100, 200), (200, 300), (300, 400), (400, 500)]
    return {f"{start}-{end}": data[(data["pressure"] >= start) & (data["pressure"] < end)][var].values
            for start, end in ranges}

def boxplot_depth_binned(errorDF, plotvar='lincal_error', 
                         var_unit = 'Nitrate error [µmol/kg]',
                         ax=None, 
                         textsize=10, 
                         boxcolor='r', boxwidths=0.55,
                         add_vlines = True, show_outliers=False, lw=1.5):    
    """ 
    Boxplot of validation errors binned by depth.
    Currently set to pressure range 0-500 dbar.
    """
    pressure_ranges = [(0, 100), (100, 200), (200, 300), (300, 400), (400, 500)]
    bias_binned = get_depth_bias(errorDF, pressure_ranges, var=plotvar)
    
    if ax == None:
        fig  = plt.figure(figsize=(5,6), tight_layout=True)
        ax = plt.gca()

    bplot_obj = ax.boxplot(bias_binned.values(), widths=boxwidths,
                           vert=False, showfliers=show_outliers, 
                        patch_artist=True, 
                        medianprops= {'color':boxcolor, 'linewidth':lw},
                        capprops={'color':boxcolor, 'linewidth':lw},
                        whiskerprops={'color':boxcolor, 'linewidth':lw},
                        flierprops={'markeredgecolor': 'gray', 'marker':'|', 'alpha':0.3, 'zorder':1}, #{'color':boxcolor, 'linewidth':1.5},
                        boxprops = {'color':boxcolor, 'linewidth':lw},
                        zorder=2)
    for patch, color in zip(bplot_obj['boxes'], [boxcolor]*10):
        patch.set_facecolor(mpcolors.to_rgba(color, alpha=0.4))
        
    labels = bias_binned.keys()
    ax.set_yticks(range(1, len(labels) + 1), labels, fontsize=textsize)
    ax.set_ylabel("Depths [m]", fontsize=textsize)
    ax.set_xlabel(var_unit, fontsize=textsize)
    ax.grid(axis='x', zorder=1, alpha=0.4)

    if add_vlines:
        ax.axvline(x=0.5, color='r', linestyle='dotted', linewidth=lw, alpha=0.6, zorder=0)
        ax.axvline(x=-0.5, color='r', linestyle='dotted', linewidth=lw, alpha=0.6, zorder=0)
        ax.axvline(x=0, color='k', linestyle='dotted', linewidth=lw, alpha=0.7, zorder=0)

    ax.invert_yaxis()

    return [ax, bplot_obj]


def plot_tracer_sections(platDF, axvars, axpals, axs=None):
    """ Plot multiple variable sections with the same time axis."""
    if axs is None:
        fig, axs = plt.subplots(4,1, figsize=(8, 8), layout='tight', sharex=True)
        axs = axs.flatten()

    axvars = ['CT', 'SA', 'oxygen', 'nitrate_pred']
    axpals = ['cmo.thermal', 'cmo.haline', 'cmo.dense', 'cmo.matter']
    for ind, ax in enumerate(axs):
        sca = ax.scatter(platDF.linear_time, platDF.pressure, c=platDF[axvars[ind]], s=20, marker='s', cmap=axpals[ind])
        plt.colorbar(sca, ax=ax, label=axvars[ind])
    
    ax.set_xlabel('Time')

    for ax in axs:
        ax.invert_yaxis()
        ax.set_ylabel('Pressure [dbar]')
        convert_xticks_date(ax, format='mm-dd')
        ax.set_xlim(platDF.linear_time.min(), platDF.linear_time.max())
    
    return axs


def plot_glider_predictions(glider_preds, axs=None, label_dates=False):
    """ Plot glider predictions in a time-depth section and map of trajectory."""
    if axs is None:
        fig = plt.figure(figsize=(8, 4), layout='tight')
        gs = fig.add_gridspec(1,2, width_ratios=[2, 1])
        ax1 = fig.add_subplot(gs[0,:1])
        ax2 = fig.add_subplot(gs[1:], projection=ccrs.PlateCarree())
        axs = [ax1, ax2]
    for ax in axs[:1]:
        sca = ax.scatter(glider_preds.linear_time, glider_preds.pressure, c=glider_preds.nitrate_pred, cmap=cmo.matter, s=50, marker='s')
        plt.colorbar(sca, ax=ax, label='Predicted Nitrate [µmol/kg]', shrink=0.8, orientation='horizontal')
        convert_xticks_date(ax, format='mm-dd')
        ax.set_xlim(glider_preds.linear_time.min(), glider_preds.linear_time.max())
        ax.set_ylim([0, 500])
        ax.invert_yaxis()
        ax.set_xlabel('Time')
        ax.set_ylabel('Pressure [dbar]')
    for ax in axs[1:]:
        map_study_region(ax=ax)
        plotINDEX = glider_preds.groupby('profile').first()
        ax.scatter(plotINDEX.longitude, plotINDEX.latitude, c=plotINDEX.linear_time)
        ax.set_title('Glider trajectory')
        if label_dates:
            for i in range(0, len(plotINDEX), 20):
                date = plotINDEX.datetime.astype('datetime64[ns]').iloc[i]
                ax.text(
                    plotINDEX.longitude.iloc[i],
                    plotINDEX.latitude.iloc[i],
                    date.strftime("%m-%d"),
                    fontsize=8
                )
    return axs

def convert_xticks_date(ax, format='mm-dd', xlist=None):
    """
    Reformat matplotlib x-axis ticks from YTD to datetime format for plotting
    """
    if xlist == None:
        xlist = ax.get_xticks()
        ax.set_xticks(xlist)
    else:
        ax.set_xticks(xlist)
    
    date_xlist = [linear2datetime(i) for i in xlist]
    date_xlist = [np.datetime_as_string(i) for i in date_xlist]

    if format == 'mm-dd':
        date_xlist = [i[5:10] for i in date_xlist]
    elif format == 'mm-yy':
        month_dict = {'01':'Jan', '02':'Feb', '03':'Mar', '04':'Apr', '05':'May', '06':'Jun',
                      '07':'Jul', '08':'Aug', '09':'Sep', '10':'Oct', '11':'Nov', '12':'Dec'}
        # date_xlist = [(i[5:7] + '\'' + i[2:4]) for i in date_xlist]
        date_xlist = [(month_dict[i[5:7]] + '\'' + i[2:4]) for i in date_xlist]

    ax.set_xticklabels(date_xlist)

    return ax

########################################################
########################################################
# %%  Utility functions ========
def label_run_options(run_list, prefix='feat'):
    """ 
    Convert list to a labeled dictionary.
   :param run_list: list of items to label
    """
    ascii_uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    runkeys = [prefix + ascii_uppercase[i] for i in range(len(run_list))]
    run_options = {runkeys[i]: run_list[i] for i in range(len(run_list))}

    return run_options, runkeys 

def make_run_tags(feat_options, data_options, target_options):
    """ 
    :param feat_options: dict of feature lists (make_feat_dict())
    :param data_options: dict of datasets for training, validation
                    data_options = {'float': [trainClasses_float, valClasses],
                        'ship': [trainClasses_ship, valClasses],
                        'combined': [trainClasses, valClasses]}
    :param target_options: list of target variable names"""
    # Automatically generate run tag combinations
    run_tags = []
    for key1 in feat_options.keys():
        for key2 in data_options.keys():
            for target in target_options:
                run_tags.append(key1 + '-' + key2 + '-' + target)
    return run_tags

def expand_hyperparam_tag(hyper_tag):
    """ 
    Temp function for translating a run tag e.g. "maxfeat1_minspit5_nest1000" into a dict of hyperparameters
    For real tuning, would typically automate / pass a grid of parameters to GridSearchCV or similar
    """
    maxfeat = int(hyper_tag.split('_')[0].replace('maxfeat', ''))
    minsplit = int(hyper_tag.split('_')[1].replace('minsplit', ''))
    nestimators = int(hyper_tag.split('_')[2].replace('nest', ''))
    return {'max_features': maxfeat, 'min_samples_split': minsplit, 'n_estimators': nestimators}


def expand_datetime(data, type='dataframe'):
    """ Choose "dataframe" or "dataset" type to expand datetime into year, month, day"""
    out = data.copy()
    if type == 'dataframe':
        out['year'] = data.datetime.astype('datetime64[ns]').map(lambda x: x.year)
        out['month'] = data.datetime.astype('datetime64[ns]').map(lambda x: x.month)
        out['day'] = data.datetime.astype('datetime64[ns]').map(lambda x: x.day)
    elif type == 'dataset':
        out['year'] = data.datetime.astype('datetime64[ns]').dt.year
        out['month'] = data.datetime.astype('datetime64[ns]').dt.month
        out['day'] = data.datetime.astype('datetime64[ns]').dt.day
        out = out.set_coords(['year', 'month', 'day'])
    return out

def datetime2linear(time, ref_time):
    """" Return time in YTD format from datetime format."""
    return (time - np.datetime64(ref_time))/np.timedelta64(1, 'D')

def linear2datetime(num, ref_time='2014-01-01'):
    """" Return datetime format to YTD.
    @ param num: (int) number of days since ref_time
      ref_time: (str) reference time in 'YYYY-MM-DD' format
    """
    return (num * np.timedelta64(1,'D')) + np.datetime64(ref_time)

def limit_datetime(platDF, min_time, max_time):
    plat_subset = platDF.reset_index()
    plat_subset = plat_subset[(plat_subset.datetime >  min_time) & (plat_subset.datetime < max_time)] 
    return plat_subset

def add_seasonal_sines(day_of_year):
    """ Return sinusoidal seasonal variables for a given day_of_year
    Note day_of_year can be days since the start of any reference year 
    
    :param day_of_year: (float) datetime converted to days since Jan 1 (linear_time)
    """
    day_of_year = day_of_year%365.25
    ydcos = np.cos(2*np.pi*np.array(day_of_year)/365.25)
    ydsin = np.sin(2*np.pi*np.array(day_of_year)/365.25)

    return [ydcos, ydsin]

def set_longitude_range(df, end_type = '360'):
    """ Switch between 0-360 to -180,180 range"""
    df = df.copy()
    if end_type == '180':
        inds = df['longitude']>180
        df.loc[inds, 'longitude'] = df.loc[inds, 'longitude'].apply(lambda x: x-360)
    elif end_type == '360':
        inds = df['longitude']<0
        df.loc[inds, 'longitude'] = df.loc[inds, 'longitude'].apply(lambda x: x+360)
    return df

def print_float_bounds(argo_DF):
    # print('Bounds of data: \n')
    print('Time range: \t' + str(argo_DF.datetime.min()[:10]) + ' to ' + str(argo_DF.datetime.max()[:10]))
    print('Latitude:\t' + str(argo_DF.latitude.min()) + ' to ' + str(argo_DF.latitude.max()))
    print('Longitude:\t' + str(argo_DF.longitude.min()) + ' to ' + str(argo_DF.longitude.max()))


########################################################
########################################################
# %% Argopy processing
def create_argo_dataframe(floatDS, bgc_list = []):
    """
    Return dataframe from a single core or BGC float dataset, accessed with Argopy. 
    Assumed to be used in 'expert' mode, i.e. not quality-controlled yet for BGC.
    (From Argopy, download and use .point2profile() and then .to_dataframe() to get input float dataframe)

    :param floatDS: float xr Dataset with profiles 
    :param bgc_list: list of BGC variables to include in the final dataframe
                        ex. ['pH', 'oxygen', 'nitrate'] 
    :return: floatDF (pd.DataFrame): 
    """
    floatDF = floatDS.to_dataframe().reset_index()

    # Default columns to rename, starting with necessary properties across core/bgc
    # Note that Argopy "research mode" has removed "ADJUSTED" from column names
    new_columns = {'LATITUDE':'latitude','LONGITUDE':'longitude', 'TIME':'datetime', 
                'CYCLE_NUMBER':'cycle_number', 'PLATFORM_NUMBER':'wmoid', 
                'PRES_ADJUSTED':'pressure', 'TEMP_ADJUSTED':'temperature', 'PSAL_ADJUSTED':'salinity'}
    # Rename QC and error columns
    new_columns.update({'TIME_QC': 'time_qc', 'POSITION_QC': 'position_qc', 
                        'PRES_ADJUSTED_QC': 'pressure_qc', 
                        'TEMP_ADJUSTED_QC': 'temperature_qc','PSAL_ADJUSTED_QC': 'salinity_qc'})
    new_columns.update({'PRES_ADJUSTED_ERROR': 'pres_error', 
                        'PSAL_ADJUSTED_ERROR': 'psal_error', 'TEMP_ADJUSTED_ERROR': 'temp_error'})
    
    # output_vars = new_columns.values()

    # ==================
    # Add BGC variables to the new column names
    if 'pH' in bgc_list: # expert mode
        new_columns.update({'PH_IN_SITU_TOTAL_ADJUSTED': 'pH', 'PH_IN_SITU_TOTAL_ADJUSTED_QC': 'pH_qc',
                            'PH_IN_SITU_TOTAL_ADJUSTED_ERROR': 'pH_error'})
    if 'oxygen' in bgc_list: 
        new_columns.update({'DOXY_ADJUSTED': 'oxygen', 'DOXY_ADJUSTED_QC': 'oxygen_qc',
                            'DOXY_ADJUSTED_ERROR': 'oxygen_error'})
    if 'nitrate' in bgc_list:
        new_columns.update({'NITRATE_ADJUSTED': 'nitrate', 'NITRATE_ADJUSTED_QC': 'nitrate_qc',
                            'NITRATE_ADJUSTED_ERROR': 'nitrate_error'})
    # ==================

    floatDF.rename(columns=new_columns, inplace=True)

    # Create a unique profile id to be a useful index
    # Make sure strings are zfilled so 1st and 10th profile are different
    floatDF['profid'] = floatDF.apply(lambda x: str(x.wmoid) + '_cyc' + str(x.cycle_number).zfill(3), axis=1)

    # Add calculated variables using gsw
    floatDF['SA']= gsw.SA_from_SP(floatDF['salinity'],floatDF['pressure'],floatDF['longitude'],floatDF['latitude'])
    floatDF['CT'] = gsw.CT_from_t(floatDF['SA'], floatDF['temperature'], floatDF['pressure']) 
    floatDF['sigma0'] = gsw.sigma0(floatDF.SA.values, floatDF.CT.values)
    floatDF['spice'] = gsw.spiciness0(floatDF["SA"].values, floatDF["CT"].values)

    # Turn all QC flags into strings
    qc_vars = [var for var in floatDF.columns.tolist() if '_qc' in var]
    for k in qc_vars:
        floatDF[k] = floatDF[k].astype(str)

    # Standard variable list to return (core)
    # Can reorder by changing the output_vars list 
    output_vars = ['wmoid', 'profid', 'latitude', 'longitude', 'datetime', 
            'pressure', 'CT', 'SA', 'sigma0', 'spice',
            'temperature', 'salinity',
            'temperature_qc', 'salinity_qc', 'pressure_qc',
            'time_qc', 'position_qc',
            'temp_error', 'psal_error', 'pres_error']
    
    for x in bgc_list:
        output_vars = output_vars + [x, x+'_qc', x+'_error']

    return floatDF[output_vars]

def filter_qc_flags(float_df, qc_vars = 'all', use_flags=['1', '2', '5', '8']):
        """
        Filter a dataframe based on QC flags.
        Can choose different QC flags for different variables by calling the function multiple times.
        Note Argopy has this function, but this one allows you to track #obs, filter on position QC.
        :param float_df: (pd.DataFrame) dataframe of float data
        :param qc_vars (list): list of QC variables to filter
                        default 'all' filters on any variable with '_qc' in the name
                        ['temperature_qc', 'salinity_qc', 'pressure_qc', 'time_qc', 'position_qc', 'pH_qc']
        :param use_flags : flags that pass QC; default are standard argo QC flags 1, 2, and 8
                        '1' for 'good' data (only '1' returned in 'research' mode)
                        '2' for 'probably good' data
                        '5' for 'changed' data (rare; for position qc where lat/lon was adjusted)
                        '8' for 'interpolated/estimated' data
        :return: float_qc (pd.DataFrame)
        """ 
        print('Using flags: ', use_flags)
        float_qc = float_df.copy().reset_index()
        print ('# of profiles before QC filtering: \t', len(float_qc.profid.unique()))
        print('# of obs before QC filtering: \t\t', len(float_qc), '\n')

        if qc_vars == 'all':
                qc_vars = [var for var in float_qc.columns.tolist() if '_qc' in var]
        
        # for var in qc_vars:
        #         float_qc = float_qc[float_qc[var].isin(use_flags)]
        #         print('# of obs after ', var, ': \t\t', len(float_qc))

        qc_table = pd.DataFrame(columns= (use_flags + ['nobs_dropped', 'nobs_remaining']), index=qc_vars)
        for var in qc_vars:
                prevlen = len(float_qc) # store length before filtering
                for flag in use_flags:
                        qc_table.loc[var, flag] = len(float_qc[float_qc[var] == flag])

                # Filter based on use_flags
                float_qc = float_qc[float_qc[var].isin(use_flags)]
                qc_table.loc[var, 'nobs_dropped'] = int(prevlen - len(float_qc))
                qc_table.loc[var, 'nobs_remaining'] = len(float_qc)
        
        print(qc_table)

        print ('\n# of profiles after QC filtering: \t', str(len(float_qc.profid.unique())) + '\n')
        return float_qc

# %% Glider processing 
def preload_glider():
    """ For setting up pre-loaded data """
    cugn66 = xr.open_dataset('./CUGN_line_66_2022.nc')
    gliderDS = cugn66.where(cugn66.time.dt.year == 2022, drop=True)
    gliderDF = (gliderDS.to_dataframe().dropna(subset=['temperature', 'salinity', 'doxy'])
                        .rename(columns={'lat':'latitude', 'lon':'longitude', 'time':'datetime',
                                        'doxy': 'oxygen'}))
    glider_traj0 = gliderDF.loc[pd.IndexSlice[0,:]]

    glider_traj0['pressure'] = gsw.p_from_z(-glider_traj0.reset_index()['depth'].values, glider_traj0['latitude'].values)
    glider_traj0['SA'] = gsw.SA_from_SP(glider_traj0.salinity, glider_traj0.pressure, glider_traj0.longitude, glider_traj0.latitude)
    glider_traj0['CT'] = gsw.CT_from_t(glider_traj0['SA'], glider_traj0['temperature'], glider_traj0['pressure'])
    glider_traj0['linear_time'] = datetime2linear(glider_traj0['datetime'], ref_time = '2014-01-01')
    glider_traj0['sigma0'] = gsw.sigma0(glider_traj0['SA'], glider_traj0['CT'])
    glider_traj0 = glider_traj0.rename(columns={'doxy': 'oxygen'})
    glider_traj0['ydcos'], glider_traj0['ydsin'] = add_seasonal_sines(glider_traj0.linear_time)

    gliderINDEX = glider_traj0.groupby('profile').first().dropna(subset=['temperature', 'salinity', 'oxygen'])
    gliderINDEX = expand_datetime(gliderINDEX, 'dataframe')
    
    return glider_traj0, gliderINDEX

########################################################
########################################################
