#!/usr/bin/env python3
# MIT License
#
# Copyright (c) 2020 FABRIC Testbed
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Author: Paul Ruth (pruth@renci.org)

import os
import traceback
import re

import functools
import time

import importlib.resources as pkg_resources
from typing import List

from fabrictestbed.slice_editor import Labels, ExperimentTopology, Capacities, ComponentType, ComponentModelType, ServiceType, ComponentCatalog
from fabrictestbed.slice_editor import (
    ExperimentTopology,
    Capacities
)
from fabrictestbed.slice_manager import SliceManager, Status, SliceState


from .abc_utils import AbcUtils

from .. import images


class SliceUtils(AbcUtils):
    """
    Utility class. Wraps useful functionality for Slice objects.
    """

    def __init__(self):
        """
        Constructor. Runs the AbcUtils constructor.
        """
        super().__init__()


    @staticmethod
    def delete_all_with_substring(string):
        """
        Deletes all slices with the specified substring.

        :param string: The substring to search for.
        :type string: str
        """
        slice_manager = AbcUtils.create_slice_manager()

        return_status, slices = slice_manager.slices(excludes=[SliceState.Dead,SliceState.Closing])
        if return_status != Status.OK:
            raise Exception("Failed to get slices: {}".format(slices))


        slices = list(filter(lambda x: string in x.slice_name, slices))

        for slice in slices:
            return_status, result = slice_manager.delete(slice_object=slice)
            print("Deleting Slice: {}.  Response Status {}".format(slice.slice_name,return_status))


    @staticmethod
    def delete_all():
        """
        Deletes all slices under the current user.
        """
        slice_manager = AbcUtils.create_slice_manager()

        return_status, slices = slice_manager.slices(excludes=[SliceState.Dead,SliceState.Closing])
        if return_status != Status.OK:
            raise Exception("Failed to get slices: {}".format(slices))

        for slice in slices:
            return_status, result = slice_manager.delete(slice_object=slice)
            print("Deleting Slice: {}.  Response Status {}".format(slice.slice_name,return_status))

    @staticmethod
    def delete_slice(slice_name=None, slice_id=None):
        """
        Deletes a slice using a slice name and ID.

        :param slice_name: The name of the slice to delete.
        :type slice_name: str
        :param slice_id: The ID of the slice to delete.
        :type slice_id: str
        """
        slice = SliceUtils.get_slice(slice_name=slice_name, slice_id=slice_id)

        slice_manager = AbcUtils.create_slice_manager()
        return_status, result = slice_manager.delete(slice_object=slice)
        print("Deleting Slice: {}.  Response Status {}".format(slice.slice_name,return_status))


    @staticmethod
    def get_slice(slice_name=None, slice_id=None, slice_manager=None):
        """"
        Gets a slice given its name, ID, and SliceManager.

        :param slice_name: The name of the slice to get.
        :type slice_name: str
        :param slice_id: The ID of the slice to get.
        :type slice_id: str
        :param slice_manager: The SliceManager where the slice to get is.
        :type slice_manager: SliceManager
        """
        if not slice_manager:
            slice_manager = AbcUtils.create_slice_manager()

        return_status, slices = slice_manager.slices(excludes=[SliceState.Dead,SliceState.Closing])
        if return_status != Status.OK:
            raise Exception("Failed to get slices: {}".format(slices))
        try:

            if slice_id:
                slice = list(filter(lambda x: x.slice_id == slice_id, slices))[0]
            elif slice_name:
                slice = list(filter(lambda x: x.slice_name == slice_name, slices))[0]
            else:
                raise Exception("Slice not found. Slice name or id requried. name: {}, slice_id: {}".format(str(slice_name),str(slice_id)))
        except:
            raise Exception("Slice not found name: {}, slice_id: {}".format(str(slice_name),str(slice_id)))

        return slice

    @staticmethod
    def list_all_slices(excludes=[SliceState.Dead,SliceState.Closing]):
        """
        Lists all slices.

        :param excludes: A list of SliceState to exclude. By defualt, this method excludes dead and closing slices.
        :type excludes: list[SliceState]
        """
        slice_manager = AbcUtils.create_slice_manager()

        return_status, slices = slice_manager.slices(excludes=[SliceState.Dead,SliceState.Closing])
        if return_status != Status.OK:
            raise Exception("Failed to get slices: {}".format(slices))
        try:
            for slice in slices:
                print("{} | {} | {}".format(slice.slice_name, slice.slice_id, slice.slice_state))
        except:
            raise Exception("Slice not found name: {}, slice_id: {}".format(str(slice_name),str(slice_id)))

        return slice


    @staticmethod
    def get_slice_error(slice_id):
        """
        Returns the error of a slice.

        :param slice_id: The ID of the slice with errors.
        :type slice_id: str
        :return: The errors in the slice.
        :rtype: str
        """
        slice_manager = AbcUtils.create_slice_manager()

        return_status, slices = slice_manager.slices(includes=[SliceState.Dead,SliceState.Closing,SliceState.StableError])
        if return_status != Status.OK:
            raise Exception("Failed to get slices: {}".format(slices))
        try:

            if slice_id:
                slice = list(filter(lambda x: x.slice_id == slice_id, slices))[0]
            else:
                raise Exception("Slice not found. Slice name or id requried. slice_id: {}".format(str(slice_id)))
        except Exception as e:
            print("Exception: {}".format(str(e)))
            raise Exception("Slice not found slice_id: {}".format(str(slice_id)))



        return_status, slivers = slice_manager.slivers(slice_object=slice)
        if return_status != Status.OK:
            raise Exception("Failed to get slivers: {}".format(slivers))

        return_errors = []
        for s in slivers:
            status, sliver_status = slice_manager.sliver_status(sliver=s)

            #print("Response Status {}".format(status))
            if status == Status.OK:
                #print()
                #print("Sliver Status {}".format(sliver_status))
                #print()
                #return_errors.append("Sliver: {} {}".format(s.name))
                #return_errors.append(sliver_status.notices)
                return_errors.append(sliver_status)

        return return_errors



    @staticmethod
    def wait_for_slice(slice_name=None,slice_id=None,timeout=360,interval=10,progress=False):
        """
        Wait for some slice to reach a stable state.

        :param slice_name: The name of the slice to wait for.
        :type slice_name: str
        :param slice_id: The ID of the slice to wait for.
        :type slice_id: str
        :param timeout: The amount of seconds to wait for the slice to reach a stable state.
        :type timeout: int
        :param interval: How often to check the state of the slice.
        :type interval: int
        :param progress: Show progress of slice or don't.
        :type progress: boolean
        """
        slice_manager = AbcUtils.create_slice_manager()
        slice = SliceUtils.get_slice(slice_name=slice_name, slice_id=slice_id)

        timeout_start = time.time()

        if progress: print("Waiting for slice .", end = '')
        while time.time() < timeout_start + timeout:
            return_status, slices = slice_manager.slices(excludes=[SliceState.Dead,SliceState.Closing])

            if return_status == Status.OK:
                slice = list(filter(lambda x: x.slice_name == slice.slice_name, slices))[0]
                if slice.slice_state == "StableOK":
                    if progress: print(" Slice state: {}".format(slice.slice_state))
                    return slice
                if slice.slice_state == "Closing" or slice.slice_state == "Dead" or slice.slice_state == "StableError":
                    if progress: print(" Slice state: {}".format(slice.slice_state))
                    return slice
            else:
                print(f"Failure: {slices}")

            if progress: print(".", end = '')
            time.sleep(interval)

        if time.time() >= timeout_start + timeout:
            if progress: print(" Timeout exceeded ({} sec). Slice: {} ({})".format(timeout,slice.slice_name,slice.slice_state))
            return slice
