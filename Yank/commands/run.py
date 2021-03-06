#!/usr/local/bin/env python

#=============================================================================================
# MODULE DOCSTRING
#=============================================================================================

"""
Run a YANK calculation.

"""

#=============================================================================================
# MODULE IMPORTS
#=============================================================================================

import os
import logging
logger = logging.getLogger(__name__)

from simtk import openmm
from simtk import unit
from simtk.openmm import app

from .. import utils

#=============================================================================================
# COMMAND-LINE INTERFACE
#=============================================================================================

usage = """
YANK run

Usage:
  yank run (-s=STORE | --store=STORE) [-m | --mpi] [-i=NITER | --iterations=NITER] [--platform=PLATFORM] [--precision=PRECISION] [--phase=PHASE] [-o | --online-analysis] [-v | --verbose]

Description:
  Run the calculation that has be set up previously by 'yank prepare' (see 'yank help prepare')

Required Arguments:
  -s=STORE, --store=STORE       Storage directory for NetCDF data files.

General Options:
  -i=NITER, --iterations=NITER  Number of iterations to run
  -m, --mpi                     Use MPI to parallelize the calculation
  -o, --online-analysis         Enable on-the-fly analysis
  --platform=PLATFORM           OpenMM Platform to use (Reference, CPU, OpenCL, CUDA)
  --precision=PRECISION         OpenMM Platform precision model to use (for CUDA or OpenCL only, one of {mixed, double, single})
  -v, --verbose                 Print verbose output

"""

#=============================================================================================
# COMMAND DISPATCH
#=============================================================================================

def dispatch(args):
    from ..yank import Yank

    store_directory = args['--store']

    # Set override options.
    options = dict()

    # Configure MPI, if requested.
    mpicomm = None
    if args['--mpi']:
        mpicomm = utils.initialize_mpi()
        logger.info("Initialized MPI on %d processes." % (mpicomm.size))

    # Configure logger
    utils.config_root_logger(args['--verbose'], mpicomm=mpicomm,
                             log_file_path=os.path.join(store_directory, 'run.log'))

    if args['--iterations']:
        options['number_of_iterations'] = int(args['--iterations'])
    if args['--online-analysis']:
        options['online_analysis'] = True
    if args['--platform'] not in [None, 'None']:
        options['platform'] = openmm.Platform.getPlatformByName(args['--platform'])
    if args['--precision']:
        # We need to modify the Platform object.
        if args['--platform'] is None:
            raise Exception("The --platform argument must be specified in order to specify platform precision.")

        # Set platform precision.
        precision = args['--precision']
        platform_name = args['--platform']
        logger.info("Setting %s platform to use precision model '%s'." % (platform_name, precision))
        if precision is not None:
            if platform_name == 'CUDA':
                options['platform'].setPropertyDefaultValue('CudaPrecision', precision)
            elif platform_name == 'OpenCL':
                options['platform'].setPropertyDefaultValue('OpenCLPrecision', precision)
            elif platform_name == 'CPU':
                if precision != 'mixed':
                    raise Exception("CPU platform does not support precision model '%s'; only 'mixed' is supported." % precision)
            elif platform_name == 'Reference':
                if precision != 'double':
                    raise Exception("Reference platform does not support precision model '%s'; only 'double' is supported." % precision)
            else:
                raise Exception("Platform selection logic is outdated and needs to be updated to add platform '%s'." % platform_name)

    # Create YANK object associated with data storage directory.
    yank = Yank(store_directory, mpicomm=mpicomm, **options)

    # Set YANK to resume from the store file.
    phases = None # By default, resume from all phases found in store_directory
    if args['--phase']: phases=[args['--phase']]
    yank.resume(phases=phases)

    # Run simulation.
    yank.run()

    return True
