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
# Author: Komal Thareja(kthare10@renci.org)

import tarfile
import ipywidgets as widgets
from IPython.display import display
from fabrictestbed_extensions.fablib.fablib import FablibManager
import os


class ArtifactManagerUI:
    """
    A UI class for managing and interacting with artifacts using the FablibManager.

    Attributes
    ----------
    download_dir : str
        The directory where artifacts will be downloaded.
    fablib : FablibManager
        Instance of FablibManager for interacting with artifacts.
    artifacts : list
        List of artifacts retrieved from FablibManager.
    error_output : widgets.Output
        Widget to display error messages.
    title_filter : widgets.Text
        Text input widget for filtering artifacts by title.
    grid : widgets.GridBox
        GridBox widget displaying the artifact information.
    """

    def __init__(self, fablib: FablibManager, download_dir: str="/home/fabric/work"):
        """
        Initializes the ArtifactManagerUI with a specified download directory.

        Parameters
        ----------
        download_dir : str, optional
            The directory where artifacts will be downloaded (default is "/home/fabric/work").
        """
        self.download_dir = download_dir
        self.fablib = fablib
        self.artifacts = self.fablib.get_manager().list_artifacts()
        self.error_output = widgets.Output()
        self.title_filter = widgets.Text(
            description='Filter by Title:',
            placeholder='Enter title keyword',
            layout=widgets.Layout(width='100%')
        )
        self.title_filter.observe(self.filter_artifacts, names='value')

        # Initialize grid as None
        self.grid = None

    def download_artifact_handler(self, artifact_title: str, version_urn: str, version: str):
        """
        Handler for downloading and extracting artifacts.

        Parameters
        ----------
        artifact_title : str
            The title of the artifact to download.
        version_urn : str
            The URN of the version to download.
        version : str
            The version of the artifact to download.

        Raises
        ------
        Exception
            If there is an error during the download or extraction process.
        """
        with self.error_output:
            try:
                self.error_output.clear_output()  # Clear any previous error messages
                location = self.fablib.download_artifact(download_dir=self.download_dir,
                                                         version_urn=version_urn, version=version)
                print(f"Artifact '{artifact_title}' version: '{version}' downloaded to {location} successfully!")

                # Extract the tar file at the same location
                if tarfile.is_tarfile(location):
                    with tarfile.open(location, "r:*") as tar:
                        extract_path = os.path.dirname(location)
                        tar.extractall(path=extract_path)
                        print(
                            f"Artifact '{artifact_title}' version: '{version}' extracted to {extract_path} successfully!")
                else:
                    print(f"Downloaded file '{location}' is not a valid tar file.")

            except Exception as e:
                print(f"Failed to download artifact: {e}")

    def filter_artifacts(self, change):
        """
        Filters artifacts based on the title filter text input.

        Parameters
        ----------
        change : dict
            The change dictionary containing the new value of the text input.
        """
        filter_text = self.title_filter.value.lower()
        filtered_artifacts = [artifact for artifact in self.artifacts
                              if filter_text in artifact['title'].lower()]
        self.update_ui(filtered_artifacts)

    def update_ui(self, artifacts):
        """
        Updates the UI with the given list of artifacts.

        Parameters
        ----------
        artifacts : list
            The list of artifacts to be displayed in the UI.
        """
        # Clear existing grid content, if any
        if self.grid is not None:
            self.grid.children = []  # Clear the grid's content without removing the widget itself

        # Define table headers
        headers = [
            widgets.HTML(value="<b>Title</b>"),
            widgets.HTML(value="<b>Authors</b>"),
            widgets.HTML(value="<b>Description</b>"),
            widgets.HTML(value="<b>Tags</b>"),
            widgets.HTML(value="<b>Versions</b>"),
        ]

        # Prepare grid items
        grid_items = headers.copy()

        # Build interactive UI for each artifact
        for artifact in artifacts:
            title_label = widgets.HTML(value=artifact['title'])
            authors_label = widgets.HTML(value=', '.join([author['name'] for author in artifact['authors']]))
            description_label = widgets.HTML(value=artifact['description_short'])
            tags_label = widgets.HTML(value=', '.join(artifact['tags']))

            # Version buttons in a horizontal box
            version_buttons = []
            for version in artifact["versions"]:
                button = widgets.Button(
                    description=f"Download v{version['version']}",
                    tooltip=f"Download version {version['version']}",
                    button_style='success',
                    layout=widgets.Layout(width='auto')
                )
                # Ensure unique binding for each button
                button.on_click(lambda b, artifact_title=artifact['title'], version_urn=version["urn"],
                                       version=version['version']: self.download_artifact_handler(artifact_title,
                                                                                                  version_urn, version))
                version_buttons.append(button)

            versions_box = widgets.HBox(version_buttons)

            # Append artifact details and buttons to grid items
            grid_items.extend([title_label, authors_label, description_label, tags_label, versions_box])

        # Create and display the grid layout
        if self.grid is None:
            self.grid = widgets.GridBox(
                grid_items,
                layout=widgets.Layout(
                    grid_template_columns="repeat(5, 25%)",
                    grid_gap="10px",
                    align_items="center"
                )
            )
        else:
            self.grid.children = grid_items

        # Display the filter and the grid
        display(self.title_filter)
        display(self.grid)
        display(self.error_output)

    def create_ui(self):
        """
        Creates and displays the user interface for interacting with artifacts.
        """
        self.update_ui(self.artifacts)


if __name__ == '__main__':
    # Create an instance of the class and render the UI
    artifact_manager_ui = ArtifactManagerUI(fablib=FablibManager())
    artifact_manager_ui.create_ui()
