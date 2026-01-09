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
"""FABRIC artifact management and representation.

This module provides the Artifact class for working with FABRIC artifacts
stored in the Artifact Manager service. Artifacts are reusable resources
such as code, data, images, or configurations that can be shared across
experiments and projects.
"""
import json


class Artifact:
    """Represents a FABRIC artifact with metadata and versioning details.

    An artifact captures reusable resources (code, data, images, configs)
    stored in FABRIC's Artifact Manager along with authorship, versions,
    and project associations.

    :ivar dict pretty_names: Mapping of field names to human-readable labels.
    :ivar fablib_manager: Reference to the active :class:`~fabrictestbed_extensions.fablib.fablib.FablibManager`.
    :ivar dict artifact_info: Raw artifact metadata returned by the Artifact Manager service.
    """

    pretty_names = {
        "title": "Title",
        "uuid": "ID",
        "description_short": "Short Description",
        "description_long": "Long Description",
        "project_name": "Project Name",
        "authors": "Authors",
        "versions": "Versions",
        "created": "Created",
        "modified": "Modified",
        "tags": "Tags",
    }

    def __init__(self, artifact_info: dict, fablib_manager):
        """
        Initialize an Artifact object with metadata.

        :param artifact_info: Dictionary containing artifact metadata from the
            Artifact Manager, including title, UUID, description, authors,
            versions, project information, and timestamps.
        :type artifact_info: dict

        :param fablib_manager: Reference to the FablibManager instance for accessing
            FABRIC services and configuration.
        :type fablib_manager: FablibManager
        """
        self.fablib_manager = fablib_manager
        self.artifact_info = artifact_info

    def to_json(self) -> str:
        """
        Convert the Artifact object to a JSON string.

        :return: JSON string representation of the Artifact object with 4-space indentation.
        :rtype: str
        """
        return json.dumps(self.to_dict(), indent=4)

    def get_fablib_manager(self):
        """
        Get the Fabric library manager associated with this artifact.

        :return: The Fabric library manager instance.
        :rtype: FablibManager
        """
        return self.fablib_manager

    def __str__(self) -> str:
        """
        Convert the Artifact object to a string representation in JSON format.

        :return: JSON string representation of the Artifact object.
        :rtype: str
        """
        return self.to_json()

    def to_dict(self) -> dict:
        """
        Convert artifact information into a dictionary format.

        Transforms the raw artifact metadata into a simplified dictionary
        structure suitable for display or serialization. Formats author emails
        as a comma-separated string and versions with their URNs.

        :return: Dictionary containing artifact fields including title, uuid,
            description_short, project_name, authors (comma-separated),
            versions (newline-separated version#URN pairs), visibility,
            created, and modified timestamps.
        :rtype: dict
        """
        authors = []
        for a in self.artifact_info.get("authors"):
            authors.append(a.get("email"))
        versions = []
        for v in self.artifact_info.get("versions"):
            versions.append(f"{v.get('version')}#{v.get('urn')}")
        d = {
            "title": self.artifact_info.get("title"),
            "uuid": self.artifact_info.get("uuid"),
            "description_short": self.artifact_info.get("description_short"),
            # "description_long": self.artifact_info.get("description_long"),
            "project_name": self.artifact_info.get("project_name"),
            "authors": ", ".join(authors),
            "versions": "\n".join(versions),
            "visibility": self.artifact_info.get("visibility"),
            "created": self.artifact_info.get("created"),
            "modified": self.artifact_info.get("modified"),
        }

        return d
