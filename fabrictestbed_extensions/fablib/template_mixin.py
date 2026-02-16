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
