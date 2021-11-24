#!/usr/bin/python3

import click
import itertools
import matplotlib.pyplot as plt
import numpy as np
import numpy.random as rn
import os

import analysis.emergence_calculator as em
from flock.model import FlockModel
from analysis.stats import process_space, process_angles

from typing import Any, Dict, List, Tuple


labels = {
    'avg_abs_vel': '$\\frac{1}{N v}  \\sum_i^N \mathbf{v}_{X_i}$',
    'std_angle': '$\\sigma_{\\theta}$',
    'std_dist_cmass': '$\\sigma_{X_M}$',
    'psi_cmass': '$\\psi_{x_M}$'
}
titles = {
    'avg_abs_vel': 'Absolute average normalised velocity',
    'std_angle': 'Standard deviation of particle direction',
    'std_dist_cmass': 'Standard deviation of distance from centre of mass',
    'psi_cmass': 'Emergence $\\psi$ for centre of mass'
}


def find_models(path: str, name: str) -> Dict[str, 'FlockModel']:
    dirs = [d for d in os.listdir(path)
              if os.path.isdir(os.path.join(path, d)) and name in d ]
    models = { d: FlockModel.load(os.path.join(path, d)) for d in dirs }
    return models


def aggregate_model_stats(
        models:      Dict[str, Any],
        param_list:  List[str],
        stats_names: List[str],
        skip:        int = 10
    ) -> Dict[float, Dict[float, Any]]:
    """
    For all models loaded in the given dict, compute stats, and aggregate
    them by the parameters and return dicts with the stats

    Params
    ------
    models
        as returned by find_models
    param_list
        the list of parameters by which to aggregate stats, must be included in
        the param hash of the FlockModel object
    stats_names
        statistics to compute and aggregate for the loaded models
    skip
        number of instances from the beginning of the time series to skip
        when computing averaged stats

    Returns
    ------
    statistics data from all experiments stored in models dict, in the form of
    nested dicts aggregated by model params as keys. Values are np.arrays of
    shape (T,) where each time point produces a statistic, otherwise scalars

    Example: Vicsek with params rho and eta, will return
        Dict[float, Dict[float, Any]]

        stats = { 1.0: { 0.1: { 'avg_dist_cmass': [ ... ],
                                'std_dist_cmass': [ ... ], ...

    """
    # extract the model hyper parameter names (e.g. eta, rho in Vicsek) and
    # check if the params passed to the function are correct
    model_params = set([p for m in models.values()
                          for p in m.params.keys() ])
    for p in param_list:
        if p not in model_params:
            raise ValueError(
                f"Parameter {p} passed to `aggregate_stats` not in model params")
            exit(0)

    # group experiments with the same params into batches
    # repeated experiments have '-' in name/path
    batch_names = sorted([ m for m in models.keys() if '-' not in m ])

    stats = dict()
    for batch in batch_names:
        exp_in_batch = sorted([ m for m in models.keys() if batch in m ])
        count = max([int(m.split('-')[1]) if len(m.split('-')) > 1 else 0
                        for m in exp_in_batch ]) + 1
        print(f"Processing {count} experiments for {batch} with params " +
            " ".join([ f"{p}: {models[batch].params[p]}" for p in model_params ]) )

        # build a hash of hashes grouping model parameters by the param_list
        tmp = stats
        for p in param_list:
            pval = models[batch].params[p]
            if pval not in tmp.keys():
                tmp[pval] = dict()
            tmp = tmp[pval]

        # iterate throuh all time series from all experiments with those params
        # and collect statistics
        for exp in exp_in_batch:
            m = models[exp]

            (t, n, d) = m.traj['X'].shape
            l = np.sqrt(m.params['rho'] * n)

            s  = process_space( m.traj['X'][skip:], l, m.bounds)
            s |= process_angles(m.traj['A'][skip:], m.params['v'])
            s |= { 'psi_cmass': em.emergence_psi(em.format(m.traj['X'][skip:]), s['cmass']) }

            for stat in stats_names:
                if stat in tmp.keys():
                    tmp[stat] += np.mean(s[stat])
                else:
                    tmp[stat]  = np.mean(s[stat])

        # average everything accross all experiments
        for stat in stats_names:
            tmp[stat] /= float(count)

    return stats


markers = itertools.cycle(('.', '+', '^', 'o', '*'))

def plot_2param(name: str, stats: Dict[str, Any], param: List[str], path: str):

    if len(param) != 2:
        raise ValueError(f'Can only plot aggregate plot with 2 params, but {param} given')
        exit(0)

    for val in titles.keys():
        for p0 in stats.keys():
            xval = [ p1 for p1 in stats[p0].keys() ]
            yval = [ np.mean(stats[p0][p1][val]) for p1 in xval ]

            plt.plot(xval, yval,
                linestyle = '--', marker = next(markers), c = np.random.rand(3,))
            plt.title(titles[val] + f" vs $\\{param[1]}$")
            plt.suptitle(name + f" $\\{param[0]}$ = {p0}", fontsize = 20)
            plt.xlabel('$\\eta$',   fontsize = 14)
            plt.ylabel(labels[val], fontsize = 14)
            plt.savefig(f"{path}/{name}_{param[0]}{p0}_{param[1]}_vs_{val}.png")
            plt.cla()


def plot_3param(name: str, stats: Dict[str, Any], param: List[str], path: str):

    if len(param) != 3:
        raise ValueError(f'Can only plot aggregate plot with 3 params, but {param} given')
        exit(0)

    markers = itertools.cycle(('.', '+', '^', 'o', '*'))
    for val in titles.keys():
        for p0 in stats.keys():
            xval = [ p1 for p1 in stats[p0].keys() ]

            groups = list(set([ p2 for p1 in xval for p2 in stats[p0][p1].keys() ]))
            for p2 in groups:
                yval = [ np.mean(stats[p0][p1][p2][val]) for p1 in xval
                                                         if p2 in stats[p0][p1].keys()]

                plt.plot(xval, yval, label = f'{param[2]} = {p2}',
                    linestyle = '--', marker = next(markers), c = np.random.rand(3,))

            plt.title(titles[val] + f" vs $\\{param[1]}$")
            plt.suptitle(name + f" $\\{param[0]}$ = {p0}", fontsize = 20)
            plt.xlabel('$\\eta$',   fontsize = 14)
            plt.ylabel(labels[val], fontsize = 14)
            plt.legend()
            plt.savefig(f"{path}/{name}_{param[0]}{p0}_{param[1]}_{param[2]}_vs_{val}.png")
            plt.cla()


@click.command()
@click.option('--path', default='out/txt/', help='Path to load model data from')
@click.option('--out',  default='out/plt/', help='Path to save plots to')
@click.option('--model', default='Vicsek_periodic_metric',  help='Model type to load')
@click.option('--aggregate', '-a', multiple = True, default=[ 'rho', 'eta' ], help='Model parameters by which it will aggregate simulations to produce stats')
def plot_results(path: str, out: str, model: str, aggregate: List[str]) -> None:
    """
    After a number of Vicsek simulations were run, aggregate multiple experiments
    with the same params and plot

    Run from the root pyflocks/ folder, e.g.

        python -m vicsek.plot_aggregate --model Vicsek -a rho -a eta -a r
    """

    if len(aggregate) > 3:
        raise ValueError("Cannot aggregate by more than 3 parameters")
        exit(0)

    models = find_models(path, model)

    if not len(models):
        print(f'No model directories of type {model} found in {path}')
        exit(0)

    stats  = aggregate_model_stats(models, aggregate, list(titles.keys()))

    plt.rcParams['figure.figsize'] = [10, 7]
    if len(aggregate) == 2:
        plot_2param(model, stats, aggregate, out)
    if len(aggregate) == 3:
        plot_3param(model, stats, aggregate, out)


if __name__ == "__main__":
    plot_results()