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

from .abc_fablib import AbcFabLIB

from .. import images


class fablib(AbcFabLIB):

    def __init__(self):
        """
        Constructor
        :return:
        """
        super().__init__()

    @staticmethod
    def new_slice(name):
        #fabric = fablib()
        from fabrictestbed_extensions.fablib.slice import Slice
        return Slice(name=name)

    @staticmethod
    def get_site_advertisment(site):
        fabric = fablib()
        #slice_manager = AbcFabricX.create_slice_manager()

        return_status, topology = fabric.slice_manager.resources()
        if return_status != Status.OK:
            raise Exception("Failed to get advertised_topology: {}, {}".format(return_status, topology))


        return topology.sites[site]

    @staticmethod
    def get_available_resources():
        fabric = fablib()
        #slice_manager = AbcFabricX.create_slice_manager()

        return_status, topology = fabric.slice_manager.resources()
        if return_status != Status.OK:
            raise Exception("Failed to get advertised_topology: {}, {}".format(return_status, topology))

        return topology

    @staticmethod
    def get_slices(excludes=[SliceState.Dead,SliceState.Closing], verbose=False):
        fabric = fablib()
        from fabrictestbed_extensions.fablib.slice import Slice

        return_status, slices = fabric.slice_manager.slices(excludes=excludes)

        return_slices = []
        if return_status == Status.OK:
            for slice in slices:
                #print("{}:".format(slice.slice_name))
                #print("   ID         : {}".format(slice.slice_id))
                #print("   State      : {}".format(slice.slice_state))
                #print("   Lease End  : {}".format(slice.lease_end))
                #print()
                return_slices.append(Slice(slice=slice))
        else:
            print(f"Failure: {slices}")

        return return_slices

    @staticmethod
    def get_slice(name=None, slice_id=None, verbose=False):
        fabric = fablib()
        #from fabrictestbed_extensions.fablib.slice import Slice

        slices = fabric.get_slices()

        for slice in slices:
            if name != None and slice.get_name() == name:
                return slice
            if slice_id != None and slice.get_slice_id() == slice_id:
                return slice

        return None

    @staticmethod
    def delete_slice(slice_name=None, slice_id=None):
        fabric = fablib()
        slice = fabric.get_slice(slice_id=slice_id)
        slice.delete()

    @staticmethod
    def delete_all():
        fabric = fablib()
        slices = fabric.get_slices()

        for slice in slices:
            try:
                slice.delete()
            except Exception as e:
                print(f"Failed to delete {slice.get_name()}")


    #TODO
    def get_slice_error(slice_id):
        fabric = fablib()
        slice_manager = AbcFabricX.create_slice_manager()

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
