from __future__ import annotations

from abc import abstractmethod
from typing import List, Optional

import jinja2


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

    def __init__(self, **kwargs):
        # V2 specific: dirty flag for caching
        self._fim_dirty: bool = True

        self._cached_reservation_id: Optional[str] = None
        self._cached_reservation_state: Optional[str] = None
        self._cached_error_message: Optional[str] = None
        self._cached_name: Optional[str] = None

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

    @abstractmethod
    def get_fim(self):
        """
        Returns fim of the template.
        """

    @abstractmethod
    def toDict(self):
        """
        Returns the attributes as a dictionary

        :return: attributes as dictionary
        :rtype: dict
        """

    def generate_template_context(self):
        """Return a dict representing this object for template rendering.

        The default implementation delegates to ``self.toDict()``.
        """
        return self.toDict()

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
                    self.get_fim().get_property(pname="reservation_info").reservation_state
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