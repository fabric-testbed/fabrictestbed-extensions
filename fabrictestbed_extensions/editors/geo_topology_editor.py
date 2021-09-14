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

import importlib.resources as pkg_resources
from typing import List

import ipywidgets as widgets
from ipywidgets import HTML, Layout
from ipyleaflet import (
    Map,
    Marker,
    Rectangle,
    WidgetControl,
    basemaps,
    Icon,
    LayerGroup,
    ZoomControl,
    AntPath,
    DrawControl,
    CircleMarker,
    FullScreenControl
)

from fabrictestbed.slice_editor import (
    ExperimentTopology,
)
from fabrictestbed.slice_manager import (
    Status,
    SliceState
)
from fabrictestbed.slice_editor import Capacities

from .abc_topology_editor import AbcTopologyEditor

from .. import images


class GeoTopologyEditor(AbcTopologyEditor):
    # Constants
    # U.S. Default Map Center
    DEFAULT_US_MAP_CENTER = (38.12480976137421, -85.7129)
    DEFAULT_US_MAP_ZOOM = 4.0
    DEFAULT_US_MAP_WIDTH = '100%'
    DEFAULT_US_MAP_HEIGHT = '650px'

    # FABRIC design elements https://fabric-testbed.net/branding/style/
    FABRIC_PRIMARY = '#27aae1'
    FABRIC_PRIMARY_LIGHT = '#cde4ef'
    FABRIC_PRIMARY_DARK = '#078ac1'
    FABRIC_SECONDARY = '#f26522'
    FABRIC_SECONDARY_LIGHT = '#ff8542'
    FABRIC_SECONDARY_DARK = '#d24502'
    FABRIC_BLACK = '#231f20'
    FABRIC_DARK = '#433f40'
    FABRIC_GREY = '#666677'
    FABRIC_LIGHT = '#f3f3f9'
    FABRIC_WHITE = '#ffffff'
    FABRIC_LOGO = "fabric_logo.png"
    SLICE_RACK_IMAGE = "http://localhost:8888/files/git/jupyter-examples/fabric_gui/slice_rack.png?_xsrf=2%7Cd383f85d%7C3663b7e992bd4ab0671df1ed48966deb%7C1630417385"
    SERVER_IMAGE = "http://localhost:8888/files/git/jupyter-examples/fabric_gui/server.png?_xsrf=2%7Cd383f85d%7C3663b7e992bd4ab0671df1ed48966deb%7C1630417385"

    # Default Widget values
    DEFAULT_SLICE_NAME_VALUE = 'New_Slice'

    DEFAULT_NODE_SELECT_VALUE = '<Choose Node>'
    DEFAULT_NODE_SITE_VALUE = '<Choose Site>'
    DEFAULT_NODE_CORE_VALUE = 1
    DEFAULT_NODE_RAM_VALUE = 6
    DEFAULT_NODE_DISK_VALUE = 4
    DEFAULT_NODE_IMAGE_VALUE = '<Choose Image>'
    DEFAULT_NODE_IMAGE_OPTIONS = [DEFAULT_NODE_IMAGE_VALUE, 'default_ubuntu_20', 'default_centos_8']
    DEFAULT_NODE_IMAGE_TYPE_VALUE = 'qcow2'
    DEFAULT_NODE_IMAGE_TYPE_OPTIONS = [DEFAULT_NODE_IMAGE_TYPE_VALUE]

    def __init__(self):
        """
        Constructor
        :return:
        """
        super().__init__()

        self.canvas = None

        self.available_resources_layer_group = None
        self.widget_layer_group = None
        self.current_slice_layer_group = None
        self.slice_layer_groups = None
        self.dashboards = None

        self.base_overflow_y = 'hidden'
        self.base_min_height = '30px'
        self.base_layout = Layout(min_height='30px', overflow_y='hidden')

        # VBox for dashbords
        self.editor_dashboard = None
        # VBox for control panel
        self.control_panel = None

        print('Creating VisualSliceEditor')
        # base layout for each line in the dashboard
        # self.base_overflow_y='hidden'
        # self.base_min_height='30px'
        # self.base_layout = Layout(min_height='30px', overflow_y='hidden')

        # TRY to remove these and use model data structures
        # HELPER/CONTAINER VARS
        # self.clusters = {}
        # self.add_btns = {}
        # self.components_dict = {}
        ######################################

        # Create the Canvas
        self.canvas = Map(basemap=basemaps.Esri.WorldStreetMap,
                          center=self.DEFAULT_US_MAP_CENTER,
                          zoom=self.DEFAULT_US_MAP_ZOOM,
                          zoom_control=False,
                          layout=Layout(width=self.DEFAULT_US_MAP_WIDTH,
                                        height=self.DEFAULT_US_MAP_HEIGHT))

        # LayerGroup for all sites remove_layer
        self.available_resources_layer_group = LayerGroup(layers=())
        # LayerGroup for all widgets and interface
        self.widget_layer_group = LayerGroup(layers=())
        # List of a LayerGroups, one for each slice (one for now)
        self.current_slice_layer_group = LayerGroup(layers=())
        self.slice_layer_groups = [self.current_slice_layer_group]

        # Add LayerGroups to Canvas
        self.canvas.add_layer(self.available_resources_layer_group)
        self.canvas.add_layer(self.widget_layer_group)
        self.canvas.add_layer(self.current_slice_layer_group)

        #logo_file_path = pkg_resources.read_binary(images, self.FABRIC_LOGO)
        #file = open(logo_file_path, "rb")
        #image = file.read()
        image = pkg_resources.read_binary(images, self.FABRIC_LOGO)
        title_widget = widgets.Image(
            value=image,
            format='png',
            width=300,
            # height=400,
        )

        title_control = WidgetControl(widget=title_widget, position='topleft')
        self.widget_layer_group.add_layer(title_widget)
        self.canvas.add_control(title_control)

        # INIALIZE Editing Dashboard
        self.editor_dashboard = widgets.VBox(layout=Layout(height='470px', width='250px', padding="4px",
                                                           overflow_y='scroll', flex_flow='column', display='flex'))

        editor_dashboard_control = WidgetControl(widget=self.editor_dashboard, position='topright')
        self.canvas.add_control(editor_dashboard_control)

        self.dashboards = {'slice_dashboard': {}, 'link_dashboard': {}}

        self.dashboards['slice_dashboard']['widget_list'] = self.init_slice_dashboard()
        self.init_node_dashboard()
        self.dashboards['link_dashboard']['widget_list'] = self.init_link_dashboard()

        # Set defaul dashboard to slice_dashboard
        self.editor_dashboard.children = self.dashboards['slice_dashboard']['widget_list']

        # Initialize control panel
        self.control_panel = widgets.VBox(layout=Layout(height='135px', width='250px', overflow_y='auto',
                                                        padding="4px"))
        control_panel_control = WidgetControl(widget=self.control_panel, position='bottomright')
        self.canvas.add_control(control_panel_control)

        # DELETE ALL BTN
        delete_all_nodes = widgets.Button(
            description='Clear All',
            disabled=False,
            tooltip='click to remove all nodes',
            layout=Layout(width='120px'))
        delete_all_nodes.style.button_color = self.FABRIC_PRIMARY
        delete_all_nodes.on_click(self.main_dashboard_delete_all)
        # delete_all_btn = WidgetControl(widget = delete_all_nodes, position='bottomright')
        # self.widget_layer_group.add_layer(delete_all_nodes)
        # self.canvas.add_control(delete_all_btn)

        # SUBMIT/PREVIEW BTN
        submit_request = widgets.Button(
            description='Submit',
            disabled=False,
            tooltip='click to submit',
            layout=Layout(width='120px', border='solid 2px ' + self.FABRIC_PRIMARY))
        submit_request.style.button_color = self.FABRIC_PRIMARY
        submit_request.on_click(self.slice_dashboard_submit_slice)

        # NEW LINK BTN
        edit_link = widgets.Button(
            description='Links',
            disabled=False,
            tooltip='Click to edit link',
            layout=Layout(width='120px'))
        edit_link.style.button_color = self.FABRIC_PRIMARY
        edit_link.on_click(self.set_edit_link_dashboard)

        # NEW Node BTN
        edit_node = widgets.Button(
            description='Nodes',
            disabled=False,
            tooltip='Click to edit node',
            layout=Layout(width='120px'))
        edit_node.style.button_color = self.FABRIC_PRIMARY
        edit_node.on_click(self.set_edit_node_dashboard)

        # NEW Node BTN
        edit_slice = widgets.Button(
            description='Slice',
            disabled=False,
            tooltip='Click to edit slice',
            layout=Layout(width='120px'))
        edit_slice.style.button_color = self.FABRIC_PRIMARY
        edit_slice.on_click(self.set_edit_slice_dashboard)
        edit_slice_btn = WidgetControl(widget=edit_slice, position='bottomright')

        control_panel_1_hbox = HTML('<center><b>Select Dashboard</b></center>')
        control_panel_2_hbox = widgets.HBox([edit_slice, edit_node, edit_link])
        control_panel_3_hbox = HTML('<center><b>Operations</b></center>')
        control_panel_4_hbox = widgets.HBox([submit_request, delete_all_nodes])
        self.control_panel.children = [control_panel_1_hbox,
                                       control_panel_2_hbox,
                                       control_panel_3_hbox,
                                       control_panel_4_hbox,
                                       ]

        # Add General Canvas Controls
        self.canvas.add_control(FullScreenControl(position='bottomleft'))

        zoom_control = ZoomControl(position='bottomleft')
        self.canvas.observe(self.zoom_control, names='zoom')
        self.canvas.add_control(zoom_control)
        print(zoom_control)

        # XXXXXXX EXPERIMENTAL: Draw Control for shapes on Canvas
        # DRAW CONTROL - MAYBE USE TO DRAW LINKS?
        dc = DrawControl(circlemarker={}, polygon={}, position='bottomleft')
        print(str(dc))
        feature_collection = {
            'type': 'FeatureCollection',
            'features': []}
        dc.on_draw(self.handle_draw)
        self.canvas.add_control(dc)

    def click_site(self, site_name, **kwargs):
        """
        Handle click on a site
        :param site_name: site name
        :param kwargs:
        :return:
        """
        print("click_site: " + str(kwargs))
        print("site: " + str(site_name))
        event = kwargs['event']
        coordinates = kwargs['coordinates']

        # Toggle Site detail for current experiment
        if not self.site_detail:
            self.site_detail = True

        self.redraw_slice_map()

    def dbclick_site(self, site_name, **kwargs):
        """
        Handle double click on a site
        :param site_name: site name
        :param kwargs:
        :return:
        """
        print("dbclick_site: " + str(kwargs))
        print("site: " + str(site_name))
        event = kwargs['event']
        # event.stopImmediatePropagation()

    def mouseover_site(self, site_name, **kwargs):
        """
        Handle mouse over a site
        :param site_name: site name
        :param kwargs:
        :return:
        """
        print("mouseover_site")
        print("site: " + str(site_name))
        print("double_click_zoom: " + str(self.canvas.double_click_zoom))
        self.canvas.disableDoubleClickZoom = True
        # self.canvas.double_click_zoom = False;

    def mouseout_site(self, site_name, **kwargs):
        """
        Handle mouse out on a site
        :param site_name: site name
        :param kwargs:
        :return:
        """
        print("mouseout_site")
        print("site: " + str(site_name))
        print("double_click_zoom: " + str(self.canvas.double_click_zoom))
        self.canvas.disableDoubleClickZoom = False

    @staticmethod
    def ant_path(path_name, **kwargs):
        """
        Print ant paths
        :param path_name: path name
        :param kwargs:
        :return:
        """
        print("ant_path")
        print("path_name: " + str(path_name))
        print(kwargs)

    def update_sites(self):
        """
        Update Sites
        :return:
        """
        print('Update Sites')
        # Query FABRIC for updated resources
        status, self.advertised_topology = self.slice_manager.resources()

        # Clear the resource layers
        self.available_resources_layer_group.clear_layers()

        # Add the sites
        site_name_list = []
        for site in self.advertised_topology.sites.values():
            try:
                site_marker = CircleMarker()
                site_marker.location = site.get_property("location").to_latlon()
                site_marker.radius = 10
                site_marker.color = self.FABRIC_PRIMARY
                site_marker.fill_color = self.FABRIC_PRIMARY

                self.available_resources_layer_group.add_layer(site_marker)

                site_marker.on_click(functools.partial(self.click_site, site_name=site.get_property("name")))
                site_marker.on_dblclick(functools.partial(self.dbclick_site, site_name=site.get_property("name")))
                site_marker.on_mouseover(functools.partial(self.mouseover_site, site_name=site.get_property("name")))
                site_marker.on_mouseout(functools.partial(self.mouseout_site, site_name=site.get_property("name")))
                site_name_list.append(site.get_property("name"))

            except Exception as e:
                print('Failed to add site: ' + str(site) + '. Error: ' + str(e))
                # traceback.print_exc()

        # Add the links (TODO: What will this look like?)
        # Create Links (cheating for now)
        # for link in self.advertised_topology.links.values():
        sites = []
        site_locations = []
        for site in self.advertised_topology.sites.values():
            try:
                site_locations.append(site.get_property("location").to_latlon())
                sites.append(site)
            except Exception as e:
                print('Failed to add site: ' + str(site) + '. Error: ' + str(e))
                # traceback.print_exc()

        paths = {}
        for i, site in enumerate(sites):
            # site_locations.append(site.get_property("location").to_latlon())
            path_locations = [sites[i].get_property("location").to_latlon(),
                              sites[(i + 1) % len(sites)].get_property("location").to_latlon()]
            ant_path = AntPath(
                locations=path_locations,
                dash_array=[1, 10],
                delay=1000,
                color='#7590ba',
                pulse_color=self.FABRIC_PRIMARY,
                paused=True,
                hardwareAccelerated=True,
                description='Task'
            )

            ant_path.on_click(functools.partial(self.ant_path, path_name=i))
            self.available_resources_layer_group.add_layer(ant_path)

        # Update node Dashboard
        site_name_list = ['<Choose Site>'] + sorted(site_name_list)
        site_name_widget = widgets.Dropdown(
            # placeholder='Enter Site Name',
            options=site_name_list,
            value='<Choose Site>',
            disabled=False,
            ensure_option=True,
            tooltip='Enter Site Name',
        )
        self.dashboards['node_dashboard']['site_name_widget'] = site_name_widget
        self.dashboards['node_dashboard']['site_name_hbox'] = widgets.HBox([widgets.Label(value="Site: ",
                                                                                          layout=Layout(width='70px',
                                                                                                        min_height=self.base_min_height,
                                                                                                        overflow_y=self.base_overflow_y)),
                                                                            site_name_widget], layout=self.base_layout)
        self.build_node_dashboard_widget_list()

    def init_node_dashboard(self):
        """
        Initialize Node dashboard
        :return:
        """
        dashboard = self.dashboards['node_dashboard'] = {}

        # Init a dictionary of compoenents
        dashboard['components'] = []
        dashboard['widget_list'] = []

        # Create Node Propertiees dashboard
        header = HTML('<center><b>Node Dashboard</b></center>')
        dashboard['header'] = header

        select_node_widget = widgets.Dropdown(
            options=[self.DEFAULT_NODE_SELECT_VALUE] + sorted(self.get_node_name_list()),
            value=self.DEFAULT_NODE_SELECT_VALUE,
            disabled=False,
            ensure_option=True,
            tooltip='Choose node to edit',
            layout=self.base_layout
        )
        select_node_widget.observe(self.node_dashboard_select_node_event, names='value')
        dashboard['select_node_widget'] = select_node_widget
        select_node_hbox = widgets.HBox([widgets.Label(value="Select Node: ", layout=Layout(width='150px',
                                                                                            min_height=self.base_min_height,
                                                                                            overflow_y=self.base_overflow_y)),
                                         select_node_widget], layout=self.base_layout)
        dashboard['select_node_hbox'] = select_node_hbox

        # Edit Node
        # edit_header = HTML('<center><b>Edit Node</b></center>')
        edit_header = HTML('<center><b><hr></b><b>Edit Node</b></center>')
        dashboard['edit_header'] = edit_header

        # Edit node fields
        node_name_widget = widgets.Text(
            # value='',
            placeholder='Enter Node Name',
            disabled=False,
            tooltip='Enter Node Name',
            layout=self.base_layout
        )
        # node_name_widget.observe(self.node_dashboard_node_name_event, names='value')
        dashboard['node_name_widget'] = node_name_widget
        node_name_hbox = widgets.HBox([widgets.Label(value="Name: ", layout=Layout(width='70px',
                                                                                   min_height=self.base_min_height,
                                                                                   overflow_y=self.base_overflow_y)),
                                       node_name_widget], layout=self.base_layout)
        dashboard['node_name_hbox'] = node_name_hbox

        site_name_widget = widgets.Dropdown(
            # placeholder='Enter Site Name',
            options=[self.DEFAULT_NODE_SITE_VALUE],
            value=self.DEFAULT_NODE_SITE_VALUE,
            disabled=False,
            ensure_option=True,
            tooltip='Enter Site Name',
            layout=self.base_layout
        )
        dashboard['site_name_widget'] = site_name_widget
        site_name_hbox = widgets.HBox([widgets.Label(value="Site: ", layout=Layout(width='70px',
                                                                                   min_height=self.base_min_height,
                                                                                   overflow_y=self.base_overflow_y)),
                                       site_name_widget], layout=self.base_layout)
        dashboard['site_name_hbox'] = site_name_hbox

        core_slider = widgets.IntSlider(min=2, max=32, step=2, value=self.DEFAULT_NODE_CORE_VALUE)
        core_slider_hbox = widgets.HBox([widgets.Label(value="Cores: ", layout=Layout(width='100px',
                                                                                      min_height=self.base_min_height,
                                                                                      overflow_y=self.base_overflow_y)),
                                         core_slider], layout=self.base_layout)
        dashboard['core_slider'] = core_slider
        dashboard['core_slider_hbox'] = core_slider_hbox

        ram_slider = widgets.IntSlider(min=2, max=64, step=2, value=self.DEFAULT_NODE_RAM_VALUE)
        ram_slider_hbox = widgets.HBox([widgets.Label(value="RAM (G): ", layout=Layout(width='100px',
                                                                                       min_height=self.base_min_height,
                                                                                       overflow_y=self.base_overflow_y)),
                                        ram_slider], layout=self.base_layout)
        dashboard['ram_slider'] = ram_slider
        dashboard['ram_slider_hbox'] = ram_slider_hbox

        disk_slider = widgets.FloatSlider(value=self.DEFAULT_NODE_DISK_VALUE, min=2, max=130, step=0.1,
                                          readout_format='1.0f')
        disk_slider_hbox = widgets.HBox([widgets.Label(value="Disk (G): ", layout=Layout(width='100px',
                                                                                         min_height=self.base_min_height,
                                                                                         overflow_y=self.base_overflow_y)),
                                         disk_slider], layout=self.base_layout)
        dashboard['disk_slider'] = disk_slider
        dashboard['disk_slider_hbox'] = disk_slider_hbox

        image_type_widget = widgets.Dropdown(
            # placeholder='Enter Site Name',
            options=self.DEFAULT_NODE_IMAGE_TYPE_OPTIONS,
            value=self.DEFAULT_NODE_IMAGE_TYPE_VALUE,
            disabled=False,
            ensure_option=True,
            tooltip='Choose Image Type',
            layout=self.base_layout
        )
        dashboard['image_type_widget'] = image_type_widget
        image_type_widget_hbox = widgets.HBox([widgets.Label(value="Image Type: ", layout=Layout(width='150px',
                                                                                                 min_height=self.base_min_height,
                                                                                                 overflow_y=self.base_overflow_y)),
                                               image_type_widget], layout=self.base_layout)
        dashboard['image_type_widget_hbox'] = image_type_widget_hbox

        image_widget = widgets.Dropdown(
            options=self.DEFAULT_NODE_IMAGE_OPTIONS,
            value=self.DEFAULT_NODE_IMAGE_VALUE,
            tooltip='Choose Image',
            ensure_option=True,
            disabled=False,
            layout=self.base_layout
        )
        dashboard['image_widget'] = image_widget
        image_widget_hbox = widgets.HBox([widgets.Label(value="Image: ", layout=Layout(width='150px',
                                                                                       min_height=self.base_min_height,
                                                                                       overflow_y=self.base_overflow_y)),
                                          image_widget], layout=self.base_layout)
        dashboard['image_widget_hbox'] = image_widget_hbox

        # Trying to get Accordion to work
        # edit_node_vbox = widgets.VBox([node_name_hbox,
        #                                site_name_hbox,
        #                                core_slider_hbox ,
        #                                ram_slider_hbox ,
        #                                disk_slider_hbox ,
        #                                image_widget_hbox,], layout=Layout(width='100%', min_height='300px', overflow_y='hidden'))
        # edit_node_accordion = widgets.Accordion(children=[edit_node_vbox ], layout=Layout(width='100%', min_height='300px', overflow_y='unset'))
        # edit_node_accordion.set_title(0, 'Edit Node Properties')

        # ADD NODE BTN
        save_node_btn = widgets.Button(
            description='Save',
            disabled=False,
            tooltip='Click to update or save changes to this node',
            layout=self.base_layout,
        )
        save_node_btn.style.button_color = self.FABRIC_PRIMARY
        save_node_btn.on_click(self.node_dashboard_save_node)
        dashboard['save_node_btn'] = save_node_btn

        delete_node_btn = widgets.Button(
            description='Delete',
            disabled=False,
            tooltip='click to delete node',
            layout=self.base_layout
        )
        dashboard['delete_node_btn'] = delete_node_btn
        delete_node_btn.style.button_color = self.FABRIC_PRIMARY
        delete_node_btn.on_click(self.node_dashboard_delete_node)

        add_node_btn = widgets.Button(
            description='Add',
            disabled=False,
            tooltip='click to add a new node',
            layout=self.base_layout
        )
        dashboard['add_node_btn'] = add_node_btn
        add_node_btn.style.button_color = self.FABRIC_PRIMARY
        add_node_btn.on_click(self.node_dashboard_add_node)

        node_edit_button_hbox = widgets.HBox([save_node_btn, delete_node_btn, add_node_btn], layout=self.base_layout)
        dashboard['node_edit_button_hbox'] = node_edit_button_hbox

        component_header = HTML('<center><b><hr></b><b>Components</b></center>')
        dashboard['component_header'] = component_header

        add_component_btn = widgets.Button(
            description='Add Component',
            disabled=False,
            tooltip='click to add a component',
            layout=self.base_layout
        )
        dashboard['add_component_btn'] = add_component_btn
        add_component_btn.style.button_color = self.FABRIC_PRIMARY
        add_component_btn.on_click(self.node_dashboard_add_component)
        add_component_button_hbox = widgets.HBox([add_component_btn], layout=self.base_layout)
        dashboard['add_component_button_hbox'] = add_component_button_hbox

        self.build_node_dashboard_widget_list()

    def build_node_dashboard_widget_list(self):
        """
        Build node dashboard widget list
        :return:
        """
        dashboard = self.dashboards['node_dashboard']

        node_dashboard_list = [dashboard['header'],
                               dashboard['select_node_hbox'],
                               dashboard['node_edit_button_hbox']
                               ]

        if dashboard['select_node_widget'].value != '<Choose Node>':
            node_dashboard_list += [dashboard['edit_header'],
                                    dashboard['node_name_hbox'],
                                    dashboard['site_name_hbox'],
                                    dashboard['core_slider_hbox'],
                                    dashboard['ram_slider_hbox'],
                                    dashboard['disk_slider_hbox'],
                                    dashboard['image_widget_hbox'],
                                    dashboard['component_header'],
                                    dashboard['add_component_button_hbox'],
                                    ]
            for component in dashboard['components']:
                print(component)
                node_dashboard_list.append(component['component_header'])
                node_dashboard_list.append(component['component_name_hbox'])
                node_dashboard_list.append(component['component_type_hbox'])
                node_dashboard_list.append(component['component_model_hbox'])

        dashboard['widget_list'] = node_dashboard_list

        return node_dashboard_list

    def init_slice_dashboard(self):
        """
        Initialize slice dashboard
        :return:
        """
        # Create Slice Propertiees dashboard
        dashboard = self.dashboards['slice_dashboard']

        header = HTML('<center><b>Slice Dashboard</b></center>')

        slice_select_widget = widgets.Select(
            options=[self.DEFAULT_SLICE_SELECT_VALUE],
            value=self.DEFAULT_SLICE_SELECT_VALUE,
            tooltip='Choose Slice',
            ensure_option=True,
            disabled=False,
            layout=self.base_layout
        )
        slice_select_widget.observe(self.slice_dashboard_select_slice, names='value')
        dashboard['slice_select_widget'] = slice_select_widget
        slice_select_widget_hbox = widgets.HBox([widgets.Label(value="Current Slice: ",
                                                               layout=Layout(width='150px',
                                                                             min_height=self.base_min_height,
                                                                             overflow_y=self.base_overflow_y)),
                                                 slice_select_widget], layout=self.base_layout)
        dashboard['slice_select_widget_hbox'] = slice_select_widget_hbox

        slice_name_widget = widgets.Text(
            # value='<New Slice Name>',
            placeholder='Enter New Slice Name',
            disabled=False,
            tooltip='Enter Slice Name',
            # layout=Layout(width='170px')
        )
        dashboard['slice_name_widget'] = slice_name_widget
        slice_name_hbox = widgets.HBox([widgets.Label(value="Name: ", layout=Layout(width='70px')), slice_name_widget])

        # ADD NODE BTN
        new_slice_btn = widgets.Button(
            description='New Slice',
            disabled=False,
            tooltip='click to create a new slice',
        )
        new_slice_btn.style.button_color = self.FABRIC_PRIMARY
        new_slice_btn.on_click(self.slice_dashboard_new_slice)

        update_slices_btn = widgets.Button(
            description='Update',
            disabled=False,
            tooltip='click get a the current list of slices',
        )
        update_slices_btn.style.button_color = self.FABRIC_PRIMARY
        update_slices_btn.on_click(self.slice_dashboard_update_slices)

        # open_slice_btn = widgets.Button(
        #    description='Open Slice',
        #    disabled=False,
        #    tooltip='Click to submit the slice',
        # )
        # open_slice_btn.style.button_color = self.FABRIC_PRIMARY
        # open_slice_btn.on_click(self.slice_dashboard_open_slice)

        submit_slice_btn = widgets.Button(
            description='Submit Slice',
            disabled=False,
            tooltip='Click to submit the slice',
        )
        submit_slice_btn.style.button_color = self.FABRIC_PRIMARY
        submit_slice_btn.on_click(self.slice_dashboard_submit_slice)

        delete_slice_btn = widgets.Button(
            description='Delete Slice',
            disabled=False,
            tooltip='click to delete the slice',
        )
        delete_slice_btn.style.button_color = self.FABRIC_PRIMARY
        delete_slice_btn.on_click(self.slice_dashboard_delete_slice)
        button_1_hbox = widgets.HBox([new_slice_btn, update_slices_btn])
        button_2_hbox = widgets.HBox([submit_slice_btn, delete_slice_btn])

        # Slice Status Text
        slice_status_header = HTML('<center><b>Slice Status</b></center>')

        slice_status_slice_name_label = widgets.Label(value="Slice Name: ",
                                                      layout=Layout(width='80px',
                                                                    min_height=self.base_min_height,
                                                                    overflow_y=self.base_overflow_y))
        slice_status_slice_name_value = widgets.Label(value="", layout=Layout(width='150px',
                                                                              min_height=self.base_min_height,
                                                                              overflow_y=self.base_overflow_y))
        dashboard['slice_status_slice_name_value'] = slice_status_slice_name_value
        slice_status_slice_name_widget_hbox = widgets.HBox([slice_status_slice_name_label,
                                                            slice_status_slice_name_value])

        slice_status_slice_id_label = widgets.Label(value="Slice ID: ", layout=Layout(width='80px',
                                                                                      min_height=self.base_min_height,
                                                                                      overflow_y=self.base_overflow_y))
        slice_status_slice_id_value = widgets.Label(value="", layout=Layout(width='150px',
                                                                            min_height=self.base_min_height,
                                                                            overflow_y=self.base_overflow_y))
        dashboard['slice_status_slice_id_value'] = slice_status_slice_id_value
        slice_status_slice_id_widget_hbox = widgets.HBox([slice_status_slice_id_label, slice_status_slice_id_value])

        slice_status_slice_state_label = widgets.Label(value="Slice State: ",
                                                       layout=Layout(width='80px',
                                                                     min_height=self.base_min_height,
                                                                     overflow_y=self.base_overflow_y))
        slice_status_slice_state_value = widgets.Label(value="", layout=Layout(width='150px',
                                                                               min_height=self.base_min_height,
                                                                               overflow_y=self.base_overflow_y))
        dashboard['slice_status_slice_state_value'] = slice_status_slice_state_value
        slice_status_slice_state_widget_hbox = widgets.HBox([slice_status_slice_state_label,
                                                             slice_status_slice_state_value])

        slice_status_lease_end_label = widgets.Label(value="Lease End: ",
                                                     layout=Layout(width='80px',
                                                                   min_height=self.base_min_height,
                                                                   overflow_y=self.base_overflow_y))
        slice_status_lease_end_value = widgets.Label(value="", layout=Layout(width='150px',
                                                                             min_height=self.base_min_height,
                                                                             overflow_y=self.base_overflow_y))
        dashboard['slice_status_lease_end_value'] = slice_status_lease_end_value
        slice_status_lease_end_widget_hbox = widgets.HBox([slice_status_lease_end_label, slice_status_lease_end_value])

        slice_status_graph_id_label = widgets.Label(value="Graph ID: ",
                                                    layout=Layout(width='80px',
                                                                  min_height=self.base_min_height,
                                                                  overflow_y=self.base_overflow_y))
        slice_status_graph_id_value = widgets.Label(value="",
                                                    layout=Layout(width='150px',
                                                                  min_height=self.base_min_height,
                                                                  overflow_y=self.base_overflow_y))

        dashboard['slice_status_graph_id_value'] = slice_status_graph_id_value
        slice_status_graph_id_widget_hbox = widgets.HBox([slice_status_graph_id_label, slice_status_graph_id_value])

        slice_status_vbox = widgets.VBox([slice_status_header,
                                          slice_status_slice_name_widget_hbox,
                                          slice_status_slice_id_widget_hbox,
                                          slice_status_slice_state_widget_hbox,
                                          slice_status_lease_end_widget_hbox,
                                          slice_status_graph_id_widget_hbox])

        return [header,
                slice_select_widget_hbox,
                slice_name_hbox,
                button_1_hbox,
                button_2_hbox,
                slice_status_vbox]

    def init_link_dashboard(self):
        """
        Initialize the link dashboard
        :return:
        """
        dashboard = self.dashboards['link_dashboard']

        # Create link Propertiees dashboard
        header = HTML('<center><b>Link Dashboard</b></center>')
        link_name_widget = widgets.Text(
            value='',
            placeholder='Enter Link Name',
            disabled=False,
            tooltip='Enter Link Name',
            # layout=Layout(width='170px')
        )
        dashboard['link_name_widget'] = link_name_widget
        link_name_hbox = widgets.HBox([widgets.Label(value="Name: ", layout=Layout(width='70px')), link_name_widget])
        return [header, link_name_hbox]

    def zoom_control(self, change):
        """
        Zoom control
        :param change:
        :return:
        """
        print("CHANGE: " + str(change))
        print("CANVAS: " + str(self.canvas))
        print("ZOOM: " + str(self.canvas.zoom))
        self.redraw_slice_map()

    def redraw_slice_map(self):
        """
        Redraw slice map
        :return:
        """
        print("redraw_slice_map")
        print(self.current_experiment)

        # Clear slice
        try:
            self.canvas.remove_layer(self.current_slice_layer_group)
        except Exception as e:
            print("layer group not in canvas")
        self.current_slice_layer_group.clear_layers()

        if self.current_experiment is None or 'topology' not in self.current_experiment.keys():
            print("Can not redraw map. No current topology to draw")
            return

        topology = self.current_experiment['topology']
        slice_id = self.current_experiment['slice_id']

        # slivers = self.slice_manager.slivers(slices=[self.current_experiment['slice']])
        if self.site_detail:
            print("topo nodes: " + str(self.current_experiment['topology'].nodes))

            slice_rack_markers = []
            count = 0
            for node in self.current_experiment['topology'].nodes:
                print("Node: " + str(self.current_experiment['topology'].nodes[node]))
                site = self.current_experiment['topology'].nodes[node].get_property(pname='site')
                print("sites: " + str(self.advertised_topology.sites))
                print("Site: " + site)

                location = self.advertised_topology.sites[site].get_property(pname='location').to_latlon()
                if site not in slice_rack_markers:
                    print("CREATING RECTANGLE " + str(location[1]) + ", " + str(location[0]))
                    baselength = 18.0
                    baseheight = 18.0
                    length = baselength / self.canvas.zoom
                    height = baseheight / self.canvas.zoom
                    length_offset = length / 2.0
                    height_offset = height / 2.0

                    self.rectangle = Rectangle(bounds=((location[0] + height_offset, location[1] - length_offset),
                                                       (location[0] - height_offset, location[1] + length_offset)),
                                               # self.rectangle = Rectangle(bounds=((location[0]+2,location[1]-4),(location[0]-5,location[1]+4)),
                                               color=self.FABRIC_PRIMARY,
                                               fill_color=self.FABRIC_LIGHT,
                                               fill_opacity=0.6)
                    self.current_slice_layer_group.add_layer(self.rectangle)
                    slice_rack_markers.append(site)

                print("ADDING MARKER: " + site)

                icon = Icon(icon_url=self.SERVER_IMAGE, icon_size=[50, 20])
                mark = Marker(location=self.location_plus(location, plus_x=0, plus_y=(0 - count) * 1), icon=icon)
                count += 1
                self.current_slice_layer_group.add_layer(mark)
        else:
            slice_rack_markers = []
            for node in self.current_experiment['topology'].nodes:
                print("Node: " + str(self.current_experiment['topology'].nodes[node]))
                site = self.current_experiment['topology'].nodes[node].get_property(pname='site')
                print("sites: " + str(self.advertised_topology.sites))
                print("Site: " + site)

                if site not in slice_rack_markers:
                    print("ADDING MARKER: " + site)
                    location = self.advertised_topology.sites[site].get_property(pname='location').to_latlon()
                    icon = Icon(icon_url=self.SLICE_RACK_IMAGE)
                    mark = Marker(location=location, icon=icon)
                    slice_rack_markers.append(site)
                    self.current_slice_layer_group.add_layer(mark)

        self.canvas.add_layer(self.current_slice_layer_group)

    @staticmethod
    def location_plus(location, plus_x, plus_y):
        """
        Location plus
        :param location: current location
        :param plus_x:
        :param plus_y:
        :return:
        """
        return location[0] + plus_y, location[1] + plus_x

    def update_edit_slice_dashboard(self):
        """
        Update Edit slice dashboard
        :return:
        """
        # self.build_slice_dashboard_widget_list()
        self.editor_dashboard.children = self.dashboards['slice_dashboard']['widget_list']

    def set_edit_slice_dashboard(self, button):
        """
        Set Edit slice dashboard
        :param button:
        :return:
        """
        self.update_edit_slice_dashboard()

    def rebuild_node_dashboard(self, node_name=DEFAULT_NODE_SELECT_VALUE):
        """
        Rebuild Node dashboard
        :param node_name:
        :return:
        """
        dashboard = self.dashboards['node_dashboard']
        # Init a dictionary of components
        dashboard['components'] = []

        # Update node select widget
        self.update_select_node_widget_option_name(node_name)

        dashboard['node_name_widget'].value = node_name

        if node_name == self.DEFAULT_NODE_SELECT_VALUE:
            dashboard['node_name_widget'].value = node_name
            dashboard['site_name_widget'].value = self.DEFAULT_NODE_SITE_VALUE
            dashboard['core_slider'].value = self.DEFAULT_NODE_CORE_VALUE
            dashboard['ram_slider'].value = self.DEFAULT_NODE_RAM_VALUE
            dashboard['disk_slider'].value = self.DEFAULT_NODE_DISK_VALUE
            dashboard['image_type_widget'].value = self.DEFAULT_NODE_IMAGE_TYPE_VALUE
            dashboard['image_widget'].value = self.DEFAULT_NODE_IMAGE_VALUE

        self.build_node_dashboard_widget_list()
        self.editor_dashboard.children = self.dashboards['node_dashboard']['widget_list']

    def set_edit_node_dashboard(self, button):
        """
        Set Edit node dashboard
        :param button:
        :return:
        """
        self.rebuild_node_dashboard()

    def update_edit_link_dashboard(self):
        """
        Update Edit Link dashboard
        :return:
        """
        # self.build_link_dashboard_widget_list()
        self.editor_dashboard.children = self.dashboards['link_dashboard']['widget_list']

    def set_edit_link_dashboard(self, button):
        """
        Set edit link dashboard
        :param button:
        :return:
        """
        self.update_edit_link_dashboard()

    def add_node(self, node_name):
        """
        Add node
        :param node_name:
        :return:
        """
        try:
            # Add to FABRIC experiment topology
            new_node = self.current_experiment['topology'].add_node(name=node_name, site=self.DEFAULT_NODE_SITE_VALUE)
            cap = Capacities()
            cap.set_fields(core=self.DEFAULT_NODE_CORE_VALUE, ram=self.DEFAULT_NODE_RAM_VALUE,
                           disk=self.DEFAULT_NODE_DISK_VALUE)
            new_node.set_properties(capacities=cap, image_type=self.DEFAULT_NODE_IMAGE_TYPE_VALUE,
                                    image_ref=self.DEFAULT_NODE_IMAGE_VALUE)

            # Update the map markers/connections

            # Update node dashboard values
            self.dashboards['node_dashboard']['node_name_widget'].value = node_name
            self.dashboards['node_dashboard']['site_name_widget'].value = self.DEFAULT_NODE_SITE_VALUE
            self.dashboards['node_dashboard']['core_slider'].value = self.DEFAULT_NODE_CORE_VALUE
            self.dashboards['node_dashboard']['ram_slider'].value = self.DEFAULT_NODE_RAM_VALUE
            self.dashboards['node_dashboard']['disk_slider'].value = self.DEFAULT_NODE_DISK_VALUE
            self.dashboards['node_dashboard']['image_widget'].value = self.DEFAULT_NODE_IMAGE_VALUE
            self.dashboards['node_dashboard']['image_type_widget'].value = self.DEFAULT_NODE_IMAGE_TYPE_VALUE
            # self.update_select_node_widget_option_name(node_name=node_name, new_node=True)
            self.rebuild_node_dashboard(node_name=node_name)

        except Exception as e:
            # TODO: Should create popup or other user facing error message
            print('Failed to add node. Error: ' + str(e))
            traceback.print_exc()

    def save_node(self, node_name, site_name, cores, ram, disk, image, image_type):
        """
        Save node
        :param node_name:
        :param site_name:
        :param cores:
        :param ram:
        :param disk:
        :param image:
        :param image_type:
        :return:
        """
        try:
            node = self.current_experiment['topology'].nodes[node_name]

            # Save node properties to FABRIC topology
            node.set_property(pname="name", pval=node_name)
            node.set_property(pname="site", pval=site_name)

            # Set capacities
            cap = Capacities()
            cap.set_fields(core=cores, ram=ram, disk=disk)
            node.set_properties(capacities=cap, image_type=image_type, image_ref=image)
        except Exception as e:
            # TODO: Should create popup or other user facing error message
            print('Failed to save node. Error: ' + str(e))
            traceback.print_exc()

    def load_node(self, node_name):
        """
        Load a node
        :param node_name: node name
        :return:
        """
        try:
            node = self.current_experiment['topology'].nodes[node_name]

            print("load node site name: " + node.get_property(pname='site'))
            print("load node image: " + node.get_property(pname='image_ref'))

            self.dashboards['node_dashboard']['node_name_widget'].value = node_name
            self.dashboards['node_dashboard']['site_name_widget'].value = node.get_property(pname='site')
            self.dashboards['node_dashboard']['core_slider'].value = int(self.get_capacity_value(node, 'core'))
            self.dashboards['node_dashboard']['ram_slider'].value = int(self.get_capacity_value(node, 'ram'))
            self.dashboards['node_dashboard']['disk_slider'].value = float(self.get_capacity_value(node, 'disk'))
            self.dashboards['node_dashboard']['image_widget'].value = node.get_property(pname='image_ref')
            self.dashboards['node_dashboard']['image_type_widget'].value = node.get_property(pname='image_type')
        except Exception as e:
            # TODO: Should create popup or other user facing error message
            print('Failed to load node. Error: ' + str(e))
            traceback.print_exc()

    def delete_node(self, node_name):
        """
        Delete node
        :param node_name: node name
        :return:
        """
        print('Delete Node')
        try:
            node_name = self.dashboards['node_dashboard']['node_name_widget'].value

            # Delete the node from experiment
            self.current_experiment['topology'].remove_node(node_name)

            # update the node dashboard
            self.update_select_node_widget_option_name(self.DEFAULT_NODE_SELECT_VALUE)
        except Exception as e:
            # TODO: Should create popup or other user facing error message
            print('Failed to delete node. Error: ' + str(e))
            traceback.print_exc()

        # Re-draw node dashboard
        self.rebuild_node_dashboard()

    def add_component(self):
        """
        Add component
        :return:
        """
        pass

    def delete_component(self):
        """
        Delete component
        :return:
        """
        pass

    def load_component(self):
        """
        Load component
        :return:
        """
        pass

    def save_component(self):
        """
        Save component
        :return:
        """
        pass

    # Crappy work around for getting capacity values out of topology nodes
    # TODO: FIX THIS
    def get_capacity_value(self, node, name='core'):
        """
        Get capacity value
        :param node:
        :param name:
        :return:
        """
        # name options: 'core', 'ram', 'disk'
        capacities = str(node.get_property(pname='capacities'))

        capacities = capacities.replace('{', '').replace('}', '').replace('G', '').replace(' ', '')
        for line in re.split(",", capacities):
            key_val = re.split(":", line)
            if key_val[0] == name:
                return key_val[1]

    def update_select_node_widget_option_name(self, name):
        """
        Update select node widget option name
        :param name:
        :return:
        """
        self.dashboards['node_dashboard']['select_node_widget'].observe(self.node_dashboard_select_node_event, names='')
        self.dashboards['node_dashboard']['select_node_widget'].options = ['<Choose Node>'] + sorted(
            self.get_node_name_list())
        self.dashboards['node_dashboard']['select_node_widget'].value = name
        self.dashboards['node_dashboard']['select_node_widget'].observe(self.node_dashboard_select_node_event,
                                                                        names='value')

    def node_dashboard_node_name_event(self, change):
        """
        Node dashboard node name event
        :param change:
        :return:
        """
        print("node_dashboard_node_name_event")
        print(change)

        # Update the name
        old_name = self.dashboards['node_dashboard']['select_node_widget'].value
        new_name = change['new']

        self.update_select_node_widget_option_name(new_name)

    def node_dashboard_select_node_event(self, change):
        """
        Node dashboard select node event
        :param change:
        :return:
        """
        print("node_dashboard_select_node_event")
        print(change)

        # Save old node selection
        old_node_name = change['old']
        if old_node_name != self.DEFAULT_NODE_SELECT_VALUE and \
                old_node_name in self.current_experiment['topology'].nodes:
            self.save_node(node_name=old_node_name,
                           site_name=self.dashboards['node_dashboard']['site_name_widget'].value,
                           cores=self.dashboards['node_dashboard']['core_slider'].value,
                           ram=self.dashboards['node_dashboard']['ram_slider'].value,
                           disk=self.dashboards['node_dashboard']['disk_slider'].value,
                           image=self.dashboards['node_dashboard']['image_widget'].value,
                           image_type=self.dashboards['node_dashboard']['image_type_widget'].value)
        # Display new node selection
        new_node_name = change['new']
        if new_node_name != self.DEFAULT_NODE_SELECT_VALUE:
            self.load_node(new_node_name)

        # Re-draw node dashboard
        self.rebuild_node_dashboard(new_node_name)

    def node_dashboard_save_node(self, button, **kwargs):
        """
        Node dashboard save node
        :param button:
        :param kwargs:
        :return:
        """
        print('Save Node')
        try:
            self.save_node(node_name=self.dashboards['node_dashboard']['node_name_widget'].value,
                           site_name=self.dashboards['node_dashboard']['site_name_widget'].value,
                           cores=self.dashboards['node_dashboard']['core_slider'].value,
                           ram=self.dashboards['node_dashboard']['ram_slider'].value,
                           disk=self.dashboards['node_dashboard']['disk_slider'].value,
                           image=self.dashboards['node_dashboard']['image_widget'].value,
                           image_type=self.dashboards['node_dashboard']['image_type_widget'].value)
        except Exception as e:
            # TODO: Should create popup or other user facing error message
            print('Failed to save node values. Error: ' + str(e))
            traceback.print_exc()

    def node_dashboard_add_node(self, button, **kwargs):
        """
        Node dashboard add node
        :param button:
        :param kwargs:
        :return:
        """
        print('Add Node')

        self.add_node(node_name=self.get_unique_node_name())

    def node_dashboard_delete_node(self, button, **kwargs):
        """
        Node dashboard delete node
        :param button:
        :param kwargs:
        :return:
        """
        self.delete_node(node_name)

    def new_slice(self, slice_name):
        """
        Create a new slice
        :param slice_name:
        :return:
        """
        print('Create New Slice')

        try:
            # Test for unique slice name
            if slice_name is None or slice_name == '' or list(filter(lambda experiment:
                                                                     experiment['slice_name'] == slice_name,
                                                                     self.experiments)):
                # TODO: should raise Exception
                print('Failed to create new slice. Error: Name not unique or invalid ' + str(slice_name))
                return

            experiment = {'slice_name': slice_name, 'slice_id': '', 'slice_state': self.EXPERIMENT_STATE_UNSUBMITTED,
                          'lease_end': '', 'graph_id': '', 'topology': ExperimentTopology()}

            self.experiments.append(experiment)

            self.update_slice_list(current_slice_name=slice_name)
        except Exception as e:
            # TODO: Should create popup or other user facing error message
            print('Failed to create new slice. Error: ' + str(e))
            traceback.print_exc()
        pass

    def delete_slice(self, slice_name):
        """
        Delete a slice
        :param slice_name:
        :return:
        """
        print('Delete Slice')
        try:
            print("self.current_experiment: " + str(self.current_experiment))
            print("self.experiments: " + str(self.experiments))

            # Set state to self.EXPERIMENT_STATE_DELETING to unset any Unsubmitted states
            self.current_experiment['slice_state'] = self.EXPERIMENT_STATE_DELETING
            result = self.slice_manager.delete(slices=[self.current_experiment['slice']])

            # TODO eliminate race condition... need to update until delete instead of sleep
            import time
            time.sleep(1)

            self.update_slice_list()
        except Exception as e:
            # TODO: Should create popup or other user facing error message
            print('Failed to delete slice. Error: ' + str(e))
            traceback.print_exc()

    def update_node_dashboard(self):
        """
        Update node dashboard
        :return:
        """
        pass

    def update_link_dashboard(self):
        """
        Update link dashboard
        :return:
        """
        pass

    def update_slice_list(self, current_slice_name=None, excludes=[SliceState.Dead, SliceState.Closing]) -> List[str]:
        """
        Update Slice list
        :param current_slice_name:
        :param excludes:
        :return:
        """
        slice_names = super().update_slice_list(current_slice_name=current_slice_name, excludes=excludes)

        self.dashboards['slice_dashboard']['slice_select_widget'].options = sorted(slice_names)
        self.dashboards['slice_dashboard']['slice_select_widget'].value = current_slice_name

        if self.current_experiment is not None:
            self.dashboards['slice_dashboard']['slice_status_slice_name_value'].value = self.current_experiment[
                'slice_name']
            self.dashboards['slice_dashboard']['slice_status_slice_id_value'].value = self.current_experiment['slice_id']
            self.dashboards['slice_dashboard']['slice_status_slice_state_value'].value = self.current_experiment[
                'slice_state']
            self.dashboards['slice_dashboard']['slice_status_lease_end_value'].value = self.current_experiment['lease_end']
            self.dashboards['slice_dashboard']['slice_status_graph_id_value'].value = self.current_experiment['graph_id']

        return slice_names

    def submit_slice(self):
        """
        Submit Slice
        :return:
        """
        self.update_slice_list()
        pass

    def open_slice_from_file(self, file_name):
        """
        Open existing slice from a file
        :param file_name:
        :return:
        """
        print("TODO open_slice_from_file")

    def save_slice_to_file(self, file_name):
        """
        Save slice to a file
        :param file_name:
        :return:
        """
        print("TODO save_slice_to_file")

    def slice_dashboard_select_slice(self, change, **kwargs):
        """
        Slice dashboard select slice
        :param change:
        :param kwargs:
        :return:
        """
        self.update_slice_list(current_slice_name=change.new)
        self.redraw_slice_map()

    def slice_dashboard_update_slices(self, button, **kwargs):
        """
        Slice dashboard update slice
        :param button:
        :param kwargs:
        :return:
        """
        current_slice_name = None
        if self.current_experiment:
            current_slice_name = self.current_experiment['slice_name']

        self.update_slice_list(current_slice_name=current_slice_name)

    def slice_dashboard_open_slice(self, button, **kwargs):
        """
        Slice dashboard open slice
        :param button:
        :param kwargs:
        :return:
        """
        self.open_slice_from_file("GET FILE NAME/PATH FROM DASHBOARD")

    def slice_dashboard_new_slice(self, button, **kwargs):
        """
        Slice dashboard new slice
        :param button:
        :param kwargs:
        :return:
        """
        self.new_slice(self.dashboards['slice_dashboard']['slice_name_widget'].value)
        # unset the new slice name
        self.dashboards['slice_dashboard']['slice_name_widget'].value = ''

    def slice_dashboard_delete_slice(self, button, **kwargs):
        """
        Slice dashboard delete slice
        :param button:
        :param kwargs:
        :return:
        """
        self.delete_slice(self.dashboards['slice_dashboard']['slice_select_widget'].value)

    def slice_dashboard_submit_slice(self, button, **kwargs):
        """
        Slice dashboard submit slice
        :param button:
        :param kwargs:
        :return:
        """
        slice_name = self.dashboards['slice_dashboard']['slice_select_widget'].value
        self.current_slice_name = slice_name
        # Generate Slice Graph
        slice_graph = self.current_experiment['topology'].serialize()

        # Request slice from Orchestrator
        status, reservations = self.slice_manager.create(slice_name=self.current_slice_name, slice_graph=slice_graph,
                                                         ssh_key=self.ssh_key)

        print("Response Status {}".format(status))
        if status == Status.OK:
            print("Reservations created {}".format(reservations))
        else:
            print(f"Failure: {reservations}")

        self.current_experiment['slice_state'] = self.EXPERIMENT_STATE_SUBMITTED
        self.update_slice_list(current_slice_name=self.current_experiment['slice_name'])

    def node_dashboard_add_component(self, button, **kwargs):
        """
        Node dashboard add component
        :param button:
        :param kwargs:
        :return:
        """
        # Add a compopnent to the current node dashboard
        print("node_dashboard_add_component")
        dashboard = self.dashboards['node_dashboard']
        component_widgets = {}

        # Edit Node
        component_header = HTML('<center><b><hr></b></center>')
        component_widgets['component_header'] = component_header

        initial_unique_component_name = self.get_unique_component_name()
        print("initial_unique_node_name: " + initial_unique_component_name)
        # Edit node fields
        component_name_widget = widgets.Text(
            value=initial_unique_component_name,
            placeholder='Enter Component Name',
            disabled=False,
            tooltip='Enter Component Name',
            layout=self.base_layout
        )
        component_widgets['component_name_widget'] = component_name_widget
        component_name_hbox = widgets.HBox([widgets.Label(value="Name: ",
                                                          layout=Layout(width='70px',
                                                                        min_height=self.base_min_height,
                                                                        overflow_y=self.base_overflow_y)),
                                            component_name_widget], layout=self.base_layout)
        component_widgets['component_name_hbox'] = component_name_hbox

        component_type_widget = widgets.Dropdown(
            options=['<Any Type>'] + sorted(self.get_component_type_list()),
            value='<Any Type>',
            disabled=False,
            ensure_option=True,
            tooltip='Choose Component Type',
            layout=self.base_layout
        )
        component_widgets['component_type_widget'] = component_type_widget
        component_type_hbox = widgets.HBox([widgets.Label(value="Type: ",
                                                          layout=Layout(width='70px',
                                                                        min_height=self.base_min_height,
                                                                        overflow_y=self.base_overflow_y)),
                                            component_type_widget], layout=self.base_layout)
        component_widgets['component_type_hbox'] = component_type_hbox

        component_model_widget = widgets.Dropdown(
            options=['<Choose Component Model>'] + self.get_component_widget_options_list(),
            value='<Choose Component Model>',
            disabled=False,
            ensure_option=True,
            tooltip='Choose Component Model',
            layout=self.base_layout
        )
        component_widgets['component_model_widget'] = component_model_widget
        component_model_hbox = widgets.HBox([widgets.Label(value="Model: ",
                                                           layout=Layout(width='70px',
                                                                         min_height=self.base_min_height,
                                                                         overflow_y=self.base_overflow_y)),
                                             component_model_widget], layout=self.base_layout)
        component_widgets['component_model_hbox'] = component_model_hbox

        dashboard = self.dashboards['node_dashboard']['components'].append(component_widgets)

        self.rebuild_node_dashboard()

    def main_dashboard_delete_all(self, button, **kwargs):
        """
        Main dashboard delete all
        :param button:
        :param kwargs:
        :return:
        """
        print("main_dashboard_delete_all")

    def handle_draw(self, info, **kwargs):
        """
        Handle draw
        :param info:
        :param kwargs:
        :return:
        """
        print("handle_draw")
        print(kwargs)

    def get_unique_component_name(self):
        """
        Get unique component name
        :return:
        """
        num = 1
        name = 'dev' + str(num)
        while len(list(filter(lambda x: x['component_name_widget'].value == name,
                              self.dashboards['node_dashboard']['components']))) > 0:
            num += 1
            name = 'dev' + str(num)

        return name

    def start(self):
        """
        Start the geo editors
        :return:
        """
        # TODO make site detail per slice and per site
        self.site_detail = False

        print("Token location: {}".format(self.slice_manager.token_location))
        print()

        print('Get Available Resources')
        self.update_sites()

        print('Getting current slices')
        self.update_slice_list()

        # cyTest
        # self.cyTest()

        # help(self.dashboards['node_dashboard']['site_name_widget'])

        return self.canvas
