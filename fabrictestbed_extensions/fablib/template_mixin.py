from __future__ import annotations

import json
from abc import abstractmethod
from typing import List, Optional

import jinja2
from fabrictestbed.slice_editor import UserData

from fabrictestbed_extensions.utils.utils import Utils


class TemplateMixin:
    """Mixin providing Jinja2 template rendering for FABRIC resource classes.

    Subclasses may override:

    * ``_default_skip`` – list of field names excluded from the template
      context by default (e.g. ``["ssh_command"]`` for nodes).
    * ``generate_template_context()`` – builds the dict that represents
      *this* object inside the template namespace.
    * ``_configure_template_environment(environment)`` – hook for
      customising the :class:`jinja2.Environment` before rendering.
    """

    _default_skip: Optional[List[str]] = None
    _show_title: str = ""

    def __init__(self, **kwargs):
        # V2 specific: dirty flag for caching
        self._fim_dirty: bool = True

        self._cached_reservation_id: Optional[str] = None
        self._cached_reservation_state: Optional[str] = None
        self._cached_error_message: Optional[str] = None
        self._cached_name: Optional[str] = None
        self._cached_dict: Optional[dict] = None

    def _invalidate_cache(self):
        """
        Invalidate all cached properties.

        Called when the FIM node is updated.
        """
        self._fim_dirty = True
        self._cached_reservation_id = None
        self._cached_reservation_state = None
        self._cached_error_message = None
        self._cached_name = None
        self._cached_dict = None

    @abstractmethod
    def get_fim(self):
        """
        Returns fim of the template.
        """

    @abstractmethod
    def toDict(self, skip: Optional[List[str]]):
        """
        Returns the attributes as a dictionary

        :return: attributes as dictionary
        :rtype: dict
        """

    def generate_template_context(self, skip: Optional[List[str]] = None):
        """Return a dict representing this object for template rendering.

        The default implementation delegates to ``self.toDict()``.
        """
        return self.toDict(skip=skip)

    def _configure_template_environment(self, environment: jinja2.Environment):
        """Hook to customise the Jinja2 environment before rendering."""
        pass

    @abstractmethod
    def get_slice(self):
        """Return a :class:`Slice` object representing the current slice."""

    def get_template_context(self, skip=None):
        """Get the full Jinja2 template context from the parent slice.

        :param skip: Field names to exclude. Falls back to
            ``_default_skip`` when *None*.
        :type skip: list[str] | None
        :return: Template context dictionary for Jinja2 rendering.
        :rtype: dict
        """
        effective_skip = skip if skip is not None else self._default_skip
        if effective_skip:
            return self.get_slice().get_template_context(self, skip=effective_skip)
        return self.get_slice().get_template_context(self)

    def render_template(self, input_string, skip=None):
        """Render a Jinja2 template string using this object's context.

        :param input_string: Jinja2 template string to render.
        :type input_string: str
        :param skip: Field names to exclude from the context.
        :type skip: list[str] | None
        :return: Rendered template output string.
        :rtype: str
        """
        environment = jinja2.Environment()
        self._configure_template_environment(environment)
        template = environment.from_string(input_string)
        return template.render(self.get_template_context(skip=skip))

    def get_error_message(self) -> str:
        """
        Gets the error messages

        :return: network service types
        :rtype: String
        """
        if self._cached_error_message is None:
            try:
                self._cached_error_message = str(
                    self.get_fim().get_property(pname="reservation_info").error_message
                )
            except Exception:
                self._cached_error_message = None
        return self._cached_error_message

    def get_reservation_id(self) -> Optional[str]:
        """
        Gets the reservation ID of the node.

        Results are cached for performance.

        :return: reservation ID
        :rtype: String
        """
        if self._cached_reservation_id is None:
            try:
                self._cached_reservation_id = str(
                    self.get_fim().get_property(pname="reservation_info").reservation_id
                )
            except Exception:
                self._cached_reservation_id = None
        return self._cached_reservation_id

    def get_reservation_state(self) -> Optional[str]:
        """
        Gets the reservation state on the FABRIC node.

        :return: the reservation state on the node
        :rtype: String
        """
        if self._cached_reservation_state is None:
            try:
                self._cached_reservation_state = str(
                    self.get_fim()
                    .get_property(pname="reservation_info")
                    .reservation_state
                )
            except Exception:
                self._cached_reservation_state = None
        return self._cached_reservation_state

    def get_name(self) -> str:
        """
        Gets the name of this network service.

        Results are cached for performance.

        :return: the name of this network service
        :rtype: String
        """
        if self._cached_name is None:
            try:
                if self.get_fim():
                    self._cached_name = self.get_fim().name
                else:
                    self._cached_name = None
            except Exception:
                self._cached_name = None
        return self._cached_name

    def toJson(self):
        """
        Returns the attributes as a JSON string.

        :return: attributes as JSON string
        :rtype: str
        """
        return json.dumps(self.toDict(), indent=4)

    def get_fablib_manager(self):
        """
        Get a reference to :py:class:`.FablibManager`.
        """
        s = self.get_slice()
        return s.get_fablib_manager() if s is not None else None

    @staticmethod
    def get_pretty_name_dict():
        """
        Return a mapping of internal field names to display names.

        Subclasses should override this to provide their own mappings.

        :return: pretty name mapping
        :rtype: dict
        """
        return {}

    def show(
        self, fields=None, output=None, quiet=False, colors=False, pretty_names=True
    ):
        """
        Show a table containing the current attributes.

        There are several output options: ``"text"``, ``"pandas"``,
        and ``"json"`` that determine the format of the output that is
        returned and (optionally) displayed/printed.

        :param output: output format
        :type output: str
        :param fields: list of fields to show
        :type fields: List[str]
        :param quiet: True to specify printing/display
        :type quiet: bool
        :param colors: True to specify state colors for pandas output
        :type colors: bool
        :param pretty_names: Display pretty names
        :type pretty_names: bool
        :return: table in format specified by output parameter
        :rtype: Object
        """
        data = self.toDict()

        if pretty_names:
            pretty_names_dict = self.get_pretty_name_dict()
        else:
            pretty_names_dict = {}

        table = Utils.show_table(
            data,
            fields=fields,
            title=self._show_title,
            output=output,
            quiet=quiet,
            pretty_names_dict=pretty_names_dict,
        )

        return table

    def set_user_data(self, user_data: dict):
        """
        Set user data.

        :param user_data: a ``dict``.
        :type user_data: dict
        """
        self.get_fim().set_property(
            pname="user_data", pval=UserData(json.dumps(user_data))
        )

    def get_user_data(self) -> dict:
        """
        Get user data.

        :return: user data dictionary
        :rtype: dict
        """
        try:
            return json.loads(str(self.get_fim().get_property(pname="user_data")))
        except Exception:
            return {}

    def get_fablib_data(self) -> dict:
        """
        Get fablib data. Usually used internally.

        :return: fablib data dictionary
        :rtype: dict
        """
        try:
            return self.get_user_data()["fablib_data"]
        except Exception:
            return {}

    def set_fablib_data(self, fablib_data: dict):
        """
        Set fablib data. Usually used internally.

        :param fablib_data: fablib data dictionary
        :type fablib_data: dict
        """
        user_data = self.get_user_data()
        user_data["fablib_data"] = fablib_data
        self.set_user_data(user_data)
