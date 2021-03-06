"""
This portion of the program is responsible for handling setup of the appropriate batch script(s) for the next step in a
Thread, passing them to a task manager to submit them, and updating the list of currently running threads accordingly.
"""

import jinja2
import os
import sys
import pickle
import shutil
import warnings
from isee.infrastructure import factory

def process(thread, running, allthreads, settings, inp_override=''):
    """
    The main function of process.py. Reads the thread to identify the next step, then builds and submits the batch
    file(s) as needed.

    Parameters
    ----------
    thread : Thread()
        The Thread object on which to act
    running : list
        The list of currently running threads, which will be updated as needed
    allthreads : list
        List of all extant threads, running or not
    settings : argparse.Namespace
        Settings namespace object
    inp_override : str
        Specified input file to use in place of the one from jobtype.get_input_file (used by initialize_charges.py)

    Returns
    -------
    running : list
        The updated list of currently running threads after this process step

    """

    # Determine next step and, if appropriate, build corresponding list of batch files
    thread.current_name = thread.get_next_step(settings)

    if thread.terminated:
        if thread in running:
            running.remove(thread)
            if running is None:
                running = []       # to keep running as a list, even if empty
        return running

    batchfiles = []         # initialize list of batch files to submit
    jobtype = factory.jobtype_factory(settings.job_type)    # get jobtype for calling jobtype.update_history
    this_inpcrd, this_top = jobtype.get_struct(thread)
    name = thread.current_name
    inp = jobtype.get_input_file(thread, settings)

    template = settings.env.get_template(thread.get_batch_template(settings))

    # todo: replace this kwargs with something appropriate for your batch template
    these_kwargs = { 'name': thread.name + '_' + name,
                     'nodes': eval('settings.nodes'),
                     'taskspernode': eval('settings.ppn'),
                     'walltime': eval('settings.walltime'),
                     'mem': eval('settings.mem'),
                     'solver': eval('settings.solver'),
                     'inp': inp,
                     'out': thread.name + '_' + name + '.out',
                     'prmtop': this_top,
                     'inpcrd': this_inpcrd,
                     'rst': thread.name + '_' + name + '.rst7',
                     'nc': thread.name + '_' + name + '.nc',
                     'working_directory': settings.working_directory,
                     'extra': eval('settings.extra') }

    filled = template.render(these_kwargs)
    newfilename = thread.name + '_' + name + '.' + settings.batch_system
    try:
        with open(newfilename, 'w') as newfile:
            newfile.write(filled)
            newfile.close()
    except OSError as e:
        if 'name too long' in str(e):
            warnings.warn('Encountered too-long filename: ' + newfilename + '. Skipping submission of this thread '
                          'to the task manager, terminating it, and continuing. Consider renaming a sample of the '
                          'initial coordinate files you like best and starting a new isEE run. If this limitation '
                          'is a problem for you, please raise an issue on GitHub detailing your use-case.')
            thread.terminated = True
            return running
        else:
            raise e

    batchfiles.append(newfilename)
    jobtype.update_history(thread, settings, **these_kwargs)

    ### Submit batch files to task manager ###
    taskmanager = factory.taskmanager_factory(settings.task_manager)
    thread.jobids = []      # to clear out previous jobids if any exist
    for file in batchfiles:
        thread.jobids.append(taskmanager.submit_batch(file, settings))

    if thread not in running:
        running.append(thread)
    return running
