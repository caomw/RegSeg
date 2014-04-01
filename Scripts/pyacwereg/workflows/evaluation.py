#!/usr/bin/env python
# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
#
# @Author: Oscar Esteban - code@oscaresteban.es
# @Date:   2014-03-12 16:59:14
# @Last Modified by:   Oscar Esteban
# @Last Modified time: 2014-04-01 16:21:05

import os
import os.path as op
import numpy as np

import nipype.interfaces.io as nio              # Data i/o
import nipype.interfaces.utility as niu         # utility
import nipype.algorithms.misc as namisc         # misc algorithms
import nipype.algorithms.mesh as namesh
from nipype.interfaces.nipy.utils import Similarity
import nipype.pipeline.engine as pe             # pipeline engine
import pyacwereg.nipype.interfaces as iface

from smri import prepare_smri
from distortion import bspline_deform
from registration import default_regseg

def registration_ev( name='EvaluateMapping', fresults='results.csv'):
    """ Workflow that provides different scores comparing two registration methods. It compares images
    similarity, displacement fields difference, mesh distances, and overlap indices.
    """

    wf = pe.Workflow( name=name )
    input_ref = pe.Node( niu.IdentityInterface( fields=[ 'in_imag',
                        'in_tpms','in_surf','in_field', 'in_mask' ] ),
                        name='refnode' )
    input_tst = pe.Node( niu.IdentityInterface( fields=['in_imag', 'in_tpms',
                                                        'in_surf','in_field' ] ),
                        name='tstnode' )
    inputnode = pe.Node( niu.IdentityInterface( fields=['subject_id', 'method']),
                         name='infonode' )
    outputnode = pe.Node(niu.IdentityInterface(fields=[ 'out_file', 'out_tpm_diff' ]),
                         name='outputnode' )

    overlap = pe.Node( namisc.FuzzyOverlap(weighting='volume'), name='Overlap' )
    row_merge = pe.Node( niu.Merge(9), name='MergeIndices')
    diff_im = pe.Node( Similarity(metric='cc'), name='ContrastDiff')
    diff_fld = pe.Node( namisc.Distance(method='eucl_max'), name='FieldDiff')
    mesh = pe.MapNode( namesh.P2PDistance(weighting='surface'),
                      iterfield=[ 'surface1','surface2' ],
                      name='SurfDistance')

    csv = pe.Node( namisc.AddCSVRow(), name="AddRow" )
    csv.inputs.in_file = fresults
    csv.inputs.field_headings = [ 'subject_id', 'method',
                                  'di_avg', 'di_tpm0', 'di_tpm1', 'di_tpm2',
                                  'ji_avg', 'ji_tpm0', 'ji_tpm1', 'ji_tpm2',
                                  'cc_im', 'max_err_field', 'err_surf' ]

    wf.connect( [
                ( inputnode,   row_merge, [( 'subject_id', 'in1'), ('method','in2')])
               ,( input_ref,     overlap, [( 'in_tpms', 'in_ref')] )
               ,( input_tst,     overlap, [( 'in_tpms', 'in_tst')] )
               ,( input_ref,     diff_im, [( 'in_imag', 'volume1'),
                                           ('in_mask','mask1'),
                                           ('in_mask','mask2')])
               ,( input_tst,     diff_im, [( 'in_imag', 'volume2')])
               ,( input_ref,    diff_fld, [( 'in_field', 'volume1'), ('in_mask','mask_volume')])
               ,( input_tst,    diff_fld, [( 'in_field', 'volume2')])
               ,( input_ref,        mesh, [( 'in_surf', 'surface1')])
               ,( input_tst,        mesh, [( 'in_surf', 'surface2')])
               ,( overlap,     row_merge, [( 'jaccard', 'in3'), ('class_fji','in4'),
                                           ( 'dice', 'in5'), ('class_fdi', 'in6') ])
               ,( diff_im,     row_merge, [( 'similarity','in7')])
               ,( diff_fld,    row_merge, [( 'distance', 'in8')])
               ,( mesh,        row_merge, [( 'distance', 'in9')])
               ,( row_merge,         csv, [( 'out', 'new_fields')])
               ,( csv,        outputnode, [( 'csv_file', 'out_file')])
               ,( overlap,    outputnode, [( 'diff_file','out_tpm_diff')])
    ])

    return wf

def bspline( name='BSplineEvaluation', methods=None ):
    """ A workflow to evaluate registration methods generating a gold standard
    with random bspline deformations.

    A list of nipype workflows can be plugged-in, using the methods input. If
    methods is None, then a default regseg method is run.


    Inputs in methods workflows
    ---------------------------

    methods workflows must define the following inputs:
        inputnode.in_surf - the input prior / surfaces in orig space
        inputnode.in_dist - the distorted images
        inputnode.in_tpms - the distorted TPMs (tissue probability maps)
        inputnode.in_orig - the original images, undistorted


    Outputs in methods workflows
    ----------------------------

        outputnode.out_corr - the distorted images, after correction
        outputnode.out_tpms - the corrected TPMs
        outputnode.out_surf - the original priors after distortion (if available)
        outputnode.out_disp - the displacement field, at image grid resoluton

    """
    wf = pe.Workflow( name=name )


    if methods is None:
        methods = [ default_regseg() ]
    else:
        methods = np.atleast_1d( methods ).tolist()

    inputnode = pe.Node( niu.IdentityInterface( fields=[ 'subject_id', 'data_dir','grid_size' ] ), name='inputnode' )
    outputnode = pe.Node(niu.IdentityInterface(fields=['out_file', 'out_tpms',
                         'out_surfs','out_field', 'out_coeff', 'out_overlap' ]),
                         name='outputnode' )

    prep = prepare_smri()
    dist = bspline_deform()

    wf.connect([
             ( inputnode,  prep, [ ('subject_id','inputnode.subject_id'),('data_dir','inputnode.data_dir') ])
            ,( inputnode,  dist, [ ('grid_size', 'inputnode.grid_size')])
            ,( prep,       dist, [ ('outputnode.out_smri_brain','inputnode.in_file'),
                                   ('outputnode.out_surfs', 'inputnode.in_surfs'),
                                   ('outputnode.out_tpms', 'inputnode.in_tpms')])
            ,( dist, outputnode, [ ('outputnode.out_file','out_file'),
                                   ('outputnode.out_field','out_field'),
                                   ('outputnode.out_coeff','out_coeff')])
    ])

    evwfs = []
    for i,reg in enumerate(methods):
        evwfs.append( registration_ev( name=('Ev_%s' % reg.name) ) )
        evwfs[i].inputs.infonode.method = reg.name
        wf.connect( [
             ( inputnode, evwfs[i], [ ('subject_id', 'infonode.subject_id')])
            ,( prep,     reg, [('outputnode.out_surfs','inputnode.in_surf'),
                               ('outputnode.out_smri_brain', 'inputnode.in_orig' ),
                               ('outputnode.out_tpms', 'inputnode.in_tpms') ])
            ,( dist,     reg, [('outputnode.out_file', 'inputnode.in_dist' )])
            ,( prep,evwfs[i], [('outputnode.out_smri_brain', 'refnode.in_imag'),
                               ('outputnode.out_tpms',       'refnode.in_tpms'),
                               ('outputnode.out_surfs',      'refnode.in_surf'),
                               ('outputnode.out_mask',       'refnode.in_mask'), ])
            ,( dist,evwfs[i], [('outputnode.out_field',      'refnode.in_field' ) ])
            ,( reg, evwfs[i], [('outputnode.out_corr', 'tstnode.in_imag'),
                               ('outputnode.out_tpms', 'tstnode.in_tpms'),
                               ('outputnode.out_surf', 'tstnode.in_surf'),
                               ('outputnode.out_field','tstnode.in_field' ) ])
        ])

    return wf
