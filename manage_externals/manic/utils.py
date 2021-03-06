#!/usr/bin/env python
"""
Common public utilities for manic package

"""

from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import print_function

import logging
import os
import string
import subprocess
import sys

from .global_constants import LOCAL_PATH_INDICATOR, LOG_FILE_NAME

# ---------------------------------------------------------------------
#
# screen and logging output
#
# ---------------------------------------------------------------------


def log_process_output(output):
    """Log each line of process output at debug level so it can be
    filtered if necessary. By default, output is a single string, and
    logging.debug(output) will only put log info heading on the first
    line. This makes it hard to filter with grep.

    """
    output = output.split('\n')
    for line in output:
        logging.debug(line)


def printlog(msg, **kwargs):
    """Wrapper script around print to ensure that everything printed to
    the screen also gets logged.

    """
    logging.info(msg)
    if kwargs:
        print(msg, **kwargs)
    else:
        print(msg)
    sys.stdout.flush()


# ---------------------------------------------------------------------
#
# error handling
#
# ---------------------------------------------------------------------
def fatal_error(message):
    """
    Error output function
    """
    logging.error(message)
    raise RuntimeError("{0}ERROR: {1}".format(os.linesep, message))


# ---------------------------------------------------------------------
#
# Data conversion / manipulation
#
# ---------------------------------------------------------------------
def str_to_bool(bool_str):
    """Convert a sting representation of as boolean into a true boolean.

    Conversion should be case insensitive.
    """
    value = None
    str_lower = bool_str.lower()
    if (str_lower == 'true') or (str_lower == 't'):
        value = True
    elif (str_lower == 'false') or (str_lower == 'f'):
        value = False
    if value is None:
        msg = ('ERROR: invalid boolean string value "{0}". '
               'Must be "true" or "false"'.format(bool_str))
        fatal_error(msg)
    return value


REMOTE_PREFIXES = ['http://', 'https://', 'ssh://', 'git@']


def is_remote_url(url):
    """check if the user provided a local file path instead of a
       remote. If so, it must be expanded to an absolute
       path.

    """
    remote_url = False
    for prefix in REMOTE_PREFIXES:
        if url.startswith(prefix):
            remote_url = True
    return remote_url


def split_remote_url(url):
    """check if the user provided a local file path or a
       remote. If remote, try to strip off protocol info.

    """
    remote_url = is_remote_url(url)
    if not remote_url:
        return url

    for prefix in REMOTE_PREFIXES:
        url = url.replace(prefix, '')

    if '@' in url:
        url = url.split('@')[1]

    if ':' in url:
        url = url.split(':')[1]

    return url


def expand_local_url(url, field):
    """check if the user provided a local file path instead of a
    remote. If so, it must be expanded to an absolute
    path.

    Note: local paths of LOCAL_PATH_INDICATOR have special meaning and
    represent local copy only, don't work with the remotes.

    """
    remote_url = is_remote_url(url)
    if not remote_url:
        if url.strip() == LOCAL_PATH_INDICATOR:
            pass
        else:
            url = os.path.expandvars(url)
            url = os.path.expanduser(url)
            if not os.path.isabs(url):
                msg = ('WARNING: Externals description for "{0}" contains a '
                       'url that is not remote and does not expand to an '
                       'absolute path. Version control operations may '
                       'fail.\n\nurl={1}'.format(field, url))
                printlog(msg)
            else:
                url = os.path.normpath(url)
    return url


# ---------------------------------------------------------------------
#
# subprocess
#
# ---------------------------------------------------------------------
def execute_subprocess(commands, status_to_caller=False,
                       output_to_caller=False):
    """Wrapper around subprocess.check_output to handle common
    exceptions.

    check_output runs a command with arguments and waits
    for it to complete.

    check_output raises an exception on a nonzero return code.  if
    status_to_caller is true, execute_subprocess returns the subprocess
    return code, otherwise execute_subprocess treats non-zero return
    status as an error and raises an exception.

    """
    msg = 'In directory: {0}\nexecute_subprocess running command:'.format(
        os.getcwd())
    logging.info(msg)
    logging.info(commands)
    return_to_caller = status_to_caller or output_to_caller
    status = -1
    output = ''
    try:
        logging.info(' '.join(commands))
        output = subprocess.check_output(commands, stderr=subprocess.STDOUT,
                                         universal_newlines=True)
        log_process_output(output)
        status = 0
    except OSError as error:
        msg = failed_command_msg(
            'Command execution failed. Does the executable exist?',
            commands)
        logging.error(error)
        fatal_error(msg)
    except ValueError as error:
        msg = failed_command_msg(
            'DEV_ERROR: Invalid arguments trying to run subprocess',
            commands)
        logging.error(error)
        fatal_error(msg)
    except subprocess.CalledProcessError as error:
        # Only report the error if we are NOT returning to the
        # caller. If we are returning to the caller, then it may be a
        # simple status check. If returning, it is the callers
        # responsibility determine if an error occurred and handle it
        # appropriately.
        if not return_to_caller:
            msg = failed_command_msg(
                'Called process did not run successfully.\n'
                'Returned status: {0}'.format(error.returncode),
                commands)
            logging.error(error)
            logging.error(msg)
            log_process_output(error.output)
            fatal_error(msg)
        status = error.returncode

    if status_to_caller and output_to_caller:
        ret_value = (status, output)
    elif status_to_caller:
        ret_value = status
    elif output_to_caller:
        ret_value = output
    else:
        ret_value = None

    return ret_value


def failed_command_msg(msg_context, command):
    """Template for consistent error messages from subprocess calls.
    """
    error_msg = string.Template("""$context
Failed command:
    $command
Please check the log file "$log" for more details.""")
    values = {
        'context': msg_context,
        'command': ' '.join(command),
        'log': LOG_FILE_NAME,
    }
    msg = error_msg.substitute(values)
    return msg
