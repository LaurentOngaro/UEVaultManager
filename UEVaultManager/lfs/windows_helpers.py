# coding=utf-8
"""
Windows specific helper functions for registry access.
"""
import ctypes


def double_clicked() -> bool:
    """
    Check if the application was started by a double click.
    """
    # Thanks https://stackoverflow.com/a/55476145

    # Load kernel32.dll
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    # Create an array to store the processes in.  This doesn't actually need to
    # be large enough to store the whole process list since GetConsoleProcess[]
    # just returns the number of processes if the array is too small.
    # noinspection PyCallingNonCallable,PyTypeChecker
    process_array = (ctypes.c_uint * 1)()
    num_processes = kernel32.GetConsoleProcessList(process_array, 1)
    return num_processes < 3
