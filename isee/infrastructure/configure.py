"""
configure.py
Takes user input file and returns settings namespace object
"""

import argparse
import pytraj       # to support pytraj calls in input file
import mdtraj       # to support mdtraj calls in the input file
import numpy        # to support numpy  calls in input file
import numpy as np  # to support numpy  calls even if called as np
import sys
import os
import shutil
import pickle
from jinja2 import Environment, FileSystemLoader
import typing
import pydantic

def configure(input_file, user_working_directory=''):
    """
    Configure the settings namespace based on the config file.

    Parameters
    ----------
    input_file : str
        Name of the configuration file to read
    user_working_directory : str
        User override for working directory (overrides value in input_file), ignored if set to ''

    Returns
    -------
    settings : argparse.Namespace
        Settings namespace object

    """

    class Settings(pydantic.BaseModel):
        # This class initializes the settings object with type hints. After being built, it gets exported as an
        # argparse.Namelist object, just for convenience.

        # Core settings required for all jobs
        job_type: str
        batch_system: str
        restart: bool
        md_engine: str
        task_manager: str = 'simple'    # 'simple' is the only implementation I wrote
        working_directory: str
        overwrite: bool

        # todo: replace the below and add your own as needed. The below lines are left in place only as an example.

        # Batch template settings
        nodes: int = 1
        ppn: int = 1
        mem: str = '4000mb'
        walltime: str = '02:00:00'
        solver: str = 'sander'
        extra: str = ''

        # File path settings
        path_to_input_files: str = os.path.dirname(os.path.realpath(__file__)) + '/data/input_files'
        path_to_templates: str = os.path.dirname(os.path.realpath(__file__)) + '/data/templates'    # todo: note that this is used below for establishing the Jinja2 environment

        # etc, etc, ...

    # Import config file line-by-line using exec()
    lines = open(input_file, 'r').readlines()
    line_index = 0
    for line in lines:      # each line in the input file is just python code setting a variable...
        line_index += 1
        try:
            exec(line)      # ... this means that comments are supported using '#' and whitespace is ignored.
        except Exception as e:
            raise ValueError('error raised while reading line ' + str(int(line_index)) + ' of configuration file '
                             + input_file + ': ' + str(e))

    # Define settings namespace to store all these variables
    config_dict = {}
    config_dict.update(locals())
    settings = argparse.Namespace()
    settings.__dict__.update(Settings(**config_dict))

    # Override working directory if provided with user_working_directory
    if user_working_directory:
        settings.working_directory = user_working_directory

    # Set Jinja2 template environment
    if os.path.exists(settings.path_to_templates):
        settings.env = Environment(loader=FileSystemLoader(settings.path_to_templates))
    else:
        raise FileNotFoundError('could not locate templates folder: ' + settings.path_to_templates)

    return settings

if __name__ == "__main__":
    configure('','')
