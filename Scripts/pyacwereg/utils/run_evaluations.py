#!/usr/bin/env python
# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
#
# @Author: oesteban - code@oscaresteban.es
# @Date:   2014-04-04 19:39:38
# @Last Modified by:   oesteban
# @Last Modified time: 2014-04-04 20:21:39

from argparse import ArgumentParser
from argparse import RawTextHelpFormatter
from os import getcwd
from shutil import copyfileobj
import os
import os.path as op
import glob

import pyacwereg.workflows.evaluation as ev


if __name__== '__main__':
    parser = ArgumentParser(description='Run evaluation workflow'
                            formatter_class=RawTextHelpFormatter)

    g_input = parser.add_argument_group('Inputs')

    g_input.add_argument('-D', '--data_dir', action='store',
                         default=os.getenv('IXI_DATASET_HOME',os.getcwd()),
                         help='directory where subjects are found')
    g_input.add_argument('-s', '--subjects', action='store',
                         default='S*', help='subject id or pattern of ids')

    g_input.add_argument('-g', '--grid_size', action='store',
                         default=[6,6,6], nargs='+',
                         help='number of control points')
    g_input.add_argument('-w', '--work_dir', action='store',
                         default=os.getcwd()),
                         help='directory where subjects are found')

    g_output = parser.add_argument_group('Outputs')
    g_output.add_argument('-o', '--out_csv', action='store',
                          help='output summary csv file')

    options = parser.parse_args()

    if not op.exists( options.work_dir ):
        os.makedirs( options.work_dir )

    subjects_dir = op.join( options.data_dir, 'subjects' )
    freesurfer_dir = op.join( options.data_dir, 'FREESURFER' )

    sub_list = glob.glob( op.join( subjects_dir, options.subjects ))
    subjects = [ op.basename( sub ) for sub in sub_list ]


    mm = ev.bspline()
    mm.base_dir = work_dir
    mm.inputs.inputnode.subject_id = subjects[0]
    mm.inputs.inputnode.data_dir = options.data_dir
    mm.inputs.inputnode.grid_size = options.grid_size

    if options.out_csv is None:
        mm.inputs.inputnode.out_csv = op.join( options.work_dir, mm.name, 'results.csv' )
    else:
        mm.inputs.inputnode.out_csv = options.out_csv

    mm.run()
