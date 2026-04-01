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
# Author: Komal Thareja (kthare10@renci.org)
import hashlib
import json
import logging
import os
import socket
from typing import Any, Callable, Dict, Iterable, List, Union

import pandas as pd
import yaml
from atomicwrites import atomic_write
from IPython import get_ipython
from IPython.core.display_functions import display
from tabulate import tabulate

from fabrictestbed_extensions.fablib.constants import Constants

log = logging.getLogger("fablib")


class Utils:
    """
    Utility helpers for FABRIC testbed operations.

    Provides reachability checks, file I/O, table formatting and
    display for both terminal and Jupyter notebook environments.
    """

    @staticmethod
    def is_reachable(*, hostname: str, port: int = 443):
        """
        Check whether a remote host is reachable via TCP.

        Resolves the hostname to all available addresses (IPv4 and IPv6)
        and attempts to connect to each.  Returns ``True`` if at least one
        connection succeeds or if the connection is blocked by a local
        firewall policy (permission denied), since that indicates the host
        is up but locally restricted.

        :param hostname: Hostname or IP address to check.
        :type hostname: str
        :param port: TCP port to connect to.
        :type port: int
        :return: ``True`` if the host is reachable.
        :rtype: bool
        :raises ConnectionError: if the hostname cannot be resolved or
            no address is reachable.
        """
        import errno

        try:
            # Get all available addresses (IPv4 and IPv6) for the hostname
            addr_info = socket.getaddrinfo(
                hostname, port, socket.AF_UNSPEC, socket.SOCK_STREAM
            )

            # Try to connect to each address until one succeeds
            errors = []
            permission_denied = False
            for family, socktype, proto, canonname, sockaddr in addr_info:
                try:
                    sock = socket.socket(family, socktype, proto)
                    sock.settimeout(5)
                    sock.connect(sockaddr)
                    sock.close()
                    return True
                except OSError as e:
                    family_name = "IPv6" if family == socket.AF_INET6 else "IPv4"

                    # EACCES (13) or EPERM (1) - permission denied by local firewall/security policy
                    # Common on VMs with restricted network policies; treat as reachable since
                    # DNS works and the block is local, not because the remote host is down
                    if e.errno in (errno.EACCES, errno.EPERM):
                        permission_denied = True
                        errors.append(
                            f"{family_name} {sockaddr[0]}: blocked by local policy"
                        )
                    # ENETUNREACH (101) - this address family isn't routable on this system
                    elif e.errno == errno.ENETUNREACH:
                        errors.append(
                            f"{family_name} {sockaddr[0]}: network unreachable"
                        )
                    else:
                        errors.append(f"{family_name} {sockaddr[0]}: {e}")
                    continue
                except socket.timeout as e:
                    errors.append(f"timeout connecting to {sockaddr[0]}: {e}")
                    continue

            # If we got permission denied, treat as reachable since DNS resolves
            # and we can't verify connectivity due to local security restrictions
            if permission_denied:
                return True

            # If we tried all addresses and none worked, raise with details
            error_details = "; ".join(errors)
            raise OSError(
                f"Could not reach {hostname}:{port}. Attempted addresses: {error_details}"
            )
        except socket.gaierror as e:
            raise ConnectionError(f"Could not resolve hostname {hostname}: {e}")
        except (socket.timeout, OSError) as e:
            raise ConnectionError(
                f"Host: {hostname} is not reachable, please check your config file! Details: {e}"
            )

    @staticmethod
    def save_to_file(file_path: str, data: str):
        """
        Write data to a file, using atomic writes when the file already exists.

        :param file_path: Path to the file.
        :type file_path: str
        :param data: Content to write.
        :type data: str
        """
        # If the file exists, use atomic_write
        if os.path.exists(file_path):
            with atomic_write(file_path, overwrite=True) as f:
                f.write(data)
        else:
            # If the file doesn't exist, create it atomically
            with open(file_path, "w") as f:
                f.write(data)

    @staticmethod
    def get_md5_fingerprint(key_string):
        """
        Compute an MD5 fingerprint of a key string.

        Returns the fingerprint in colon-separated hex format
        (e.g. ``"aa:bb:cc:..."``).

        :param key_string: The key string to fingerprint.
        :type key_string: str
        :return: Colon-separated MD5 hex digest.
        :rtype: str
        """
        key_bytes = key_string.encode("utf-8")
        md5_hash = hashlib.md5(key_bytes).hexdigest()
        return ":".join(a + b for a, b in zip(md5_hash[::2], md5_hash[1::2]))

    @staticmethod
    def is_yaml_file(file_path: str):
        """
        Check whether a file contains valid YAML content.

        :param file_path: Path to the file to check.
        :type file_path: str
        :return: ``True`` if the file contains a valid YAML dict or list,
            ``False`` otherwise (including file-not-found).
        :rtype: bool
        """
        try:
            with open(file_path, "r") as file:
                # Attempt to load the content as YAML
                yaml_content = yaml.safe_load(file)

                # Check if the loaded content is a dictionary or a list
                if isinstance(yaml_content, (dict, list)):
                    return True
                else:
                    return False

        except yaml.YAMLError:
            # Parsing failed, it's not a YAML file
            return False
        except FileNotFoundError:
            # File not found
            return False

    @staticmethod
    def read_file_contents(file_path: str) -> str:
        """
        Read and return the entire contents of a text file.

        :param file_path: Path to the file to read.
        :type file_path: str
        :return: File contents, or ``None`` if the file does not exist.
        :rtype: str
        """
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()

    @staticmethod
    def is_jupyter_notebook() -> bool:
        """
        Test for running inside a jupyter notebook

        :return: bool, True if in jupyter notebook
        :rtype: bool
        """
        try:
            shell = get_ipython().__class__.__name__
            if shell == "ZMQInteractiveShell":
                return True  # Jupyter notebook or qtconsole
            elif shell == "TerminalInteractiveShell":
                return False  # Terminal running IPython
            else:
                return False  # Other type (?)
        except NameError:
            return False

    @staticmethod
    def _show_table_text(table, quiet=False):
        """
        Make a table in text form suitable for terminal.

        You normally will not use this method directly; you should
        rather use :py:meth:`show_table()`.

        :param table: A list of lists.
        :param quiet: Setting this to `False` causes the table to be
            printed.

        :return: A table formatted by tabulate library.
        :rtype: str
        """
        printable_table = tabulate(table)

        if not quiet:
            print(f"\n{printable_table}")

        return printable_table

    @staticmethod
    def _show_table_jupyter(
        table, headers=None, title="", title_font_size="1.25em", quiet=False
    ):
        """
        Make a table in text form suitable for Jupyter notebooks.

        You normally will not use this method directly; you should
        rather use :py:meth:`show_table()`.

        :param table: A list of lists.
        :param title: The table title.
        :param title_font_size: Font size to use for the table title.
        :param quiet: Setting this to `False` causes the table to be
            displayed.

        :return: a Pandas dataframe.
        :rtype: pd.DataFrame
        """
        printable_table = pd.DataFrame(table)

        properties = {
            "text-align": "left",
            "border": f"1px {Constants.FABRIC_BLACK} solid !important",
        }

        printable_table = printable_table.style.set_caption(title)
        printable_table = printable_table.set_properties(**properties, overwrite=False)
        printable_table = printable_table.hide(axis="index")
        printable_table = printable_table.hide(axis="columns")

        printable_table = printable_table.set_table_styles(
            [
                {
                    "selector": "tr:nth-child(even)",
                    "props": [
                        ("background", f"{Constants.FABRIC_PRIMARY_EXTRA_LIGHT}"),
                        ("color", f"{Constants.FABRIC_BLACK}"),
                    ],
                }
            ],
            overwrite=False,
        )
        printable_table = printable_table.set_table_styles(
            [
                {
                    "selector": "tr:nth-child(odd)",
                    "props": [
                        ("background", f"{Constants.FABRIC_WHITE}"),
                        ("color", f"{Constants.FABRIC_BLACK}"),
                    ],
                }
            ],
            overwrite=False,
        )

        caption_props = [
            ("text-align", "center"),
            ("font-size", "150%"),
        ]

        printable_table = printable_table.set_table_styles(
            [{"selector": "caption", "props": caption_props}], overwrite=False
        )

        if not quiet:
            display(printable_table)

        return printable_table

    @staticmethod
    def _show_table_json(data, quiet=False):
        """
        Make a table in JSON format.

        You normally will not use this method directly; you should
        rather use :py:meth:`show_table()`.

        :param data: A list of lists.
        :param quiet: Setting this to `False` causes the JSON string
            to be printed.

        :return: Table in JSON format.
        :rtype: str
        """
        json_str = json.dumps(data, indent=4)

        if not quiet:
            print(f"{json_str}")

        return json_str

    @staticmethod
    def _show_table_dict(data, quiet=False):
        """
        Show the table.

        You normally will not use this method directly; you should
        rather use :py:meth:`show_table()`.

        :param data: The table as a Python object; likely a list of
            lists.
        :param quiet: Setting this to `False` causes the table to be
            printed.

        :return: The table as a Python object.
        :rtype: str
        """
        if not quiet:
            print(f"{data}")

        return data

    @staticmethod
    def show_table(
        data: Dict[str, Any],
        fields: Union[List[str], None] = None,
        title: str = "",
        title_font_size: str = "1.25em",
        output: Union[str, None] = None,
        quiet: bool = False,
        pretty_names_dict: Dict[str, str] = {},
    ):
        """
        Format and optionally display a table.

        :param data: Data to be presented in the table.

        :param fields: Table headers, as a list of strings.

        :param title: Table title.

        :param title_font_size: Font size to use in table title, when
            displaying the table in a Jupyter notebook.

        :param output: The table format.  Options are: ``"text"`` (or
            ``"default"``), or ``"json"``, or ``"dict"``, or
            ``"pandas"`` (or ``"jupyter_default"``).

        :param quiet: Display the table, in addition to returning a
            table in the required `output` format.

        :param pretty_names_dict: A mapping from non-pretty names to
            pretty names to use in table headers.

        :return: Input :py:obj:`data` formatted as a table.
        :rtype: Depends on :py:obj:`output` parameter.
        """
        output = Utils._determine_output_type(output)

        table = Utils._create_show_table(
            data, fields=fields, pretty_names_dict=pretty_names_dict
        )

        if output == "text" or output == "default":
            return Utils._show_table_text(table, quiet=quiet)
        elif output == "json":
            return Utils._show_table_json(data, quiet=quiet)
        elif output == "dict":
            return Utils._show_table_dict(data, quiet=quiet)
        elif output == "pandas" or output == "jupyter_default":
            return Utils._show_table_jupyter(
                table,
                headers=fields,
                title=title,
                title_font_size=title_font_size,
                quiet=quiet,
            )
        else:
            log.error(f"Unknown output type: {output}")

    @staticmethod
    def _list_table_text(
        table: List[List[Any]],
        headers: Union[List[str], None] = None,
        quiet: bool = False,
    ):
        """
        Format a table as text.

        This is a helper method called by :py:meth:`list_table()`; you
        should use that method instead of invoking this directly.

        :param table: A list that :py:func:`tabulate()` can use.
        :param headers: List of column headers.
        :param quiet: Print the table when ``False``.

        :return: A table-formatted string.
        """
        if headers is not None:
            printable_table = tabulate(table, headers=headers)
        else:
            printable_table = tabulate(table)

        if not quiet:
            print(f"\n{printable_table}")

        return printable_table

    @staticmethod
    def _list_table_jupyter(
        table: List[List[Any]],
        headers: Union[List[str], None] = None,
        title: str = "",
        title_font_size: str = "1.25em",
        output=None,
        quiet: bool = False,
    ):
        """
        Format a table as a Pandas DataFrame.

        This is a helper method called by :py:meth:`list_table()`; you
        should use that method instead of invoking this directly.

        :param table: A list that :py:func:`tabulate()` can use.
        :param headers: List of column headers.
        :param title: Table title, set as caption for the DataFrame.
        :param output: Unused.
        :param quiet: Display the table when ``False``.

        :return: A Pandas DataFrame.
        """
        if len(table) == 0:
            return None

        if headers is not None:
            printable_table = pd.DataFrame(table, columns=headers)
        else:
            printable_table = pd.DataFrame(table)

        properties = {
            "text-align": "left",
            "border": f"1px {Constants.FABRIC_BLACK} solid !important",
        }

        printable_table = printable_table.style.set_caption(title)
        printable_table = printable_table.hide(axis="index")
        printable_table = printable_table.set_properties(**properties, overwrite=False)

        caption_props = [
            ("text-align", "center"),
            ("font-size", "150%"),
            ("caption-side", "top"),
        ]

        printable_table = printable_table.set_table_styles(
            [{"selector": "caption", "props": caption_props}], overwrite=False
        )

        printable_table = printable_table.set_table_styles(
            [dict(selector="th", props=[("text-align", "left")])], overwrite=False
        )
        printable_table = printable_table.set_table_styles(
            [
                {
                    "selector": "tr:nth-child(even)",
                    "props": [
                        ("background", f"{Constants.FABRIC_WHITE}"),
                        ("color", f"{Constants.FABRIC_BLACK}"),
                    ],
                }
            ],
            overwrite=False,
        )
        printable_table = printable_table.set_table_styles(
            [
                {
                    "selector": "tr:nth-child(odd)",
                    "props": [
                        ("background", f"{Constants.FABRIC_PRIMARY_EXTRA_LIGHT}"),
                        ("color", f"{Constants.FABRIC_BLACK}"),
                    ],
                }
            ],
            overwrite=False,
        )

        printable_table = printable_table.set_table_styles(
            [
                dict(
                    selector=".level0",
                    props=[
                        ("border", "1px black solid !important"),
                        ("background", f"{Constants.FABRIC_WHITE}"),
                        ("color", f"{Constants.FABRIC_BLACK}"),
                    ],
                )
            ],
            overwrite=False,
        )

        if not quiet:
            display(printable_table)

        return printable_table

    @staticmethod
    def _list_table_json(data: List[Dict[str, str]], quiet: bool = False):
        """
        Return a JSON representation of tabular data.

        This is a helper method called by :py:meth:`list_table()`; you
        should use that method instead of invoking this directly.

        :param data: Data to be formatted as JSON.
        :param quiet: Prints the JSON string when ``False``.

        :return: Some JSON.
        """
        json_str = json.dumps(data, indent=4)

        if not quiet:
            print(f"{json_str}")

        return json_str

    @staticmethod
    def _list_table_list(data: List[Dict[str, str]], quiet: bool = False):
        """
        Return text representation of tabular data.

        This is a helper method called by :py:meth:`list_table()`; you
        should use that method instead of invoking this directly.

        :param data: Data to be formatted.
        :param quiet: Prints the string when ``False``.

        :return: A table-formatted string.
        """
        if not quiet:
            print(f"{data}")

        return data

    @staticmethod
    def list_table(
        data: List[Dict[str, str]],
        fields: Union[List[str], None] = None,
        title: str = "",
        title_font_size: str = "1.25em",
        output: Union[str, None] = None,
        quiet: bool = False,
        filter_function: Union[Callable[[Iterable], bool], None] = None,
        pretty_names_dict: Dict[str, str] = {},
    ):
        """
        Format a list into a table that we can display.

        :param data: Data to be formatted.
        :param fields: List of column headings.
        :param title: Table title.
        :param title_font_size: Font size of the table title.
        :param output: Output format, which can be one of ``"text"``,
            ``"json"``, ``"list"``, or ``"pandas"``.
        :param quiet: Prints the table when ``True``.
        :param filter_function: A lambda that can be used to filter
            the input data.
        :param pretty_names_dict: A mapping from non-pretty names to
            pretty names, used in column headings.

        :return: Input :py:obj:`data` formatted as a table.
        """
        output = Utils._determine_output_type(output)
        if filter_function:
            data = list(filter(filter_function, data))

        log.debug(f"data: {data}\n\n")

        if fields is None and len(pretty_names_dict) > 0:
            fields = pretty_names_dict.keys()

        if fields is None and len(data) > 0:
            fields = list(data[0].keys())

        if fields is None:
            fields = []

        log.debug(f"fields: {fields}\n\n")

        headers = []
        for field in fields:
            if field in pretty_names_dict:
                headers.append(pretty_names_dict[field])
            else:
                headers.append(field)

        log.debug(f"headers: {headers}\n\n")

        if output == "text":
            table = Utils._create_list_table(data, fields=fields)
            return Utils._list_table_text(table, headers=headers, quiet=quiet)
        elif output == "json":
            return Utils._list_table_json(data, quiet=quiet)
        elif output == "list":
            return Utils._list_table_list(data, quiet=quiet)
        elif output == "pandas":
            table = Utils._create_list_table(data, fields=fields)

            return Utils._list_table_jupyter(
                table,
                headers=headers,
                title=title,
                title_font_size=title_font_size,
                output=output,
                quiet=quiet,
            )
        else:
            log.error(f"Unknown output type: {output}")

    @staticmethod
    def _create_list_table(
        data: List[Dict[str, str]], fields: Union[List[str], None] = None
    ):
        """
        Format a list as a table.

        This method is used by :py:meth:`list_table()`; you do not
        have to use this directly.

        :param data: Data to be formatted.
        :param fields: List of column titles.

        :return: Tabular data.
        """
        table = []
        for entry in data:
            row = []
            for field in fields:
                row.append(entry.get(field, ""))

            table.append(row)
        return table

    @staticmethod
    def _create_show_table(
        data: Dict[str, Any],
        fields: Union[List[str], None] = None,
        pretty_names_dict: dict[str, str] = {},
    ) -> List[List[str]]:
        """
        Form a table that we can display.

        You should not have to use this method directly; this is used
        by :py:meth:`show_table()`.

        :param data: Input data.
        :param fields: List of column field names.
        :param pretty_names_dict: Mapping from non-pretty to pretty
            names, to be used as column labels.

        :return: A list that can be formatted as a table.
        """
        table = []
        if fields is None:
            for key, value in data.items():
                if key in pretty_names_dict:
                    table.append([pretty_names_dict[key], value])
                else:
                    table.append([key, value])
        else:
            for field in fields:
                value = data[field]
                if field in pretty_names_dict:
                    table.append([pretty_names_dict[field], value])
                else:
                    table.append([field, value])

        return table

    @staticmethod
    def calendar_to_rows(
        calendar_data: Dict[str, Any],
        show: str = "all",
    ) -> List[Dict[str, str]]:
        """
        Flatten a ``resources_calendar()`` response into tabular rows.

        Each row represents one (time-slot, site/host) pair with columns for
        date, site or host name, cores, ram, disk (as ``"available/capacity"``),
        and one column per component type.

        :param calendar_data: The dict returned by
            ``fablib.resources_calendar()`` or the orchestrator.
        :param show: Which resource types to include: ``"sites"``,
            ``"hosts"``, or ``"all"`` (default).
        :type show: str
        :return: A list of row dicts suitable for :py:meth:`list_table`.
        :rtype: list[dict]
        """
        interval = calendar_data.get("interval", "day")
        include_sites = show in ("all", "sites")
        include_hosts = show in ("all", "hosts")
        rows: List[Dict[str, str]] = []
        for slot in calendar_data.get("data", []):
            start = slot.get("start", "")
            end = slot.get("end", "")
            # Show date only for day/week, datetime for hour
            if interval in ("day", "week"):
                slot_label = start[:10] if len(start) >= 10 else start
            else:
                slot_label = start[:16] if len(start) >= 16 else start

            if include_sites:
                for site in slot.get("sites", []):
                    row: Dict[str, str] = {
                        "Date": slot_label,
                        "Type": "site",
                        "Name": site.get("name", ""),
                        "Cores (avail/cap)": f"{site.get('cores_available', '—')}/{site.get('cores_capacity', '—')}",
                        "RAM GB (avail/cap)": f"{site.get('ram_available', '—')}/{site.get('ram_capacity', '—')}",
                        "Disk GB (avail/cap)": f"{site.get('disk_available', '—')}/{site.get('disk_capacity', '—')}",
                    }
                    for comp_name, comp in site.get("components", {}).items():
                        cap = comp.get("capacity", 0)
                        if cap and cap > 0:
                            row[comp_name] = f"{comp.get('available', 0)}/{cap}"
                    rows.append(row)

            if include_hosts:
                for host in slot.get("hosts", []):
                    row: Dict[str, str] = {
                        "Date": slot_label,
                        "Type": "host",
                        "Name": host.get("name", ""),
                        "Cores (avail/cap)": f"{host.get('cores_available', '—')}/{host.get('cores_capacity', '—')}",
                        "RAM GB (avail/cap)": f"{host.get('ram_available', '—')}/{host.get('ram_capacity', '—')}",
                        "Disk GB (avail/cap)": f"{host.get('disk_available', '—')}/{host.get('disk_capacity', '—')}",
                    }
                    for comp_name, comp in host.get("components", {}).items():
                        cap = comp.get("capacity", 0)
                        if cap and cap > 0:
                            row[comp_name] = f"{comp.get('available', 0)}/{cap}"
                    rows.append(row)
        return rows

    @staticmethod
    def show_calendar(
        calendar_data: Dict[str, Any],
        show: str = "all",
        fields: Union[List[str], None] = None,
        output: Union[str, None] = None,
        quiet: bool = False,
        filter_function: Union[Callable[[Iterable], bool], None] = None,
    ):
        """
        Display a resource calendar as a formatted table.

        Converts the ``resources_calendar()`` response into rows and
        renders them using :py:meth:`list_table`.

        :param calendar_data: The dict returned by
            ``fablib.resources_calendar()``.
        :param show: Which resource types to include: ``"sites"``,
            ``"hosts"``, or ``"all"`` (default).
        :type show: str
        :param fields: Columns to include.  ``None`` means all.
        :param output: Output format (``"text"``, ``"json"``,
            ``"pandas"``, ``"list"``).  Auto-detected if ``None``.
        :param quiet: Suppress printing when ``True``.
        :param filter_function: A lambda to filter the flattened rows.
        :return: Formatted table.
        """
        rows = Utils.calendar_to_rows(calendar_data, show=show)
        interval = calendar_data.get("interval", "day")
        q_start = calendar_data.get("query_start", "")[:10]
        q_end = calendar_data.get("query_end", "")[:10]
        title = f"Resource Calendar ({interval} interval, {q_start} to {q_end})"
        return Utils.list_table(
            data=rows,
            fields=fields,
            title=title,
            output=output,
            quiet=quiet,
            filter_function=filter_function,
        )

    @staticmethod
    def _determine_output_type(output: Union[str, None]) -> str:
        """
        Determine the output format based on the running environment.

        If *output* is ``None``, returns ``"pandas"`` when running inside
        a Jupyter notebook, or ``"text"`` otherwise.

        :param output: Explicit output type, or ``None`` for auto-detect.
        :type output: str or None
        :return: The resolved output type string.
        :rtype: str
        """
        if output is None:
            if Utils.is_jupyter_notebook():
                output = "pandas"
            else:
                output = "text"
        return output
