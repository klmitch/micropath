# Copyright (C) 2018 by Kevin L. Mitchell <klmitch@mit.edu>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you
# may not use this file except in compliance with the License. You may
# obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied. See the License for the specific language governing
# permissions and limitations under the License.

import six

from micropath import elements


class ControllerMeta(type):
    """
    Metaclass for controllers.  This metaclass takes care of the task
    of collecting routing elements defined in the class's namespace
    and putting them into a single routing tree.
    """

    def __new__(cls, name, bases, namespace):
        """
        Construct a new ``Controller`` subclass.

        :param str name: The name of the new class.
        :param bases: A tuple of base classes.
        :type bases: ``tuple`` of classes
        :param dict namespace: The namespace of the new class.

        :returns: A newly constructed subclass of the ``Controller``
                  class.
        """

        # Construct a new Root
        root = elements.Root()

        # Collect handlers
        handlers = {}

        # Walk the namespace looking for elements and callables with
        # Method elements
        for ident, value in namespace.items():
            # Add elements to the root
            if isinstance(value, elements.Element):
                root.add_elem(value, ident)
                continue

            # Add HTTP methods to the root as well
            if hasattr(value, '_micropath_methods'):
                for meth in value._micropath_methods:
                    root.add_elem(meth, ident)

            # Collect the list of handlers
            if getattr(value, '_micropath_handler', False):
                handlers[ident] = value

        # Add the root and handlers list to the namespace
        namespace.update(
            _micropath_root=root,
            _micropath_handlers=handlers,
        )

        return super(ControllerMeta, cls).__new__(cls, name, bases, namespace)


@six.add_metaclass(ControllerMeta)
class Controller(object):
    """
    Controller class.  This is the central type for routing URL paths
    and HTTP methods to actual handlers.  See the
    ``micropath.path()``, ``micropath.bind()``, and
    ``micropath.mount()`` functions and the ``@micropath.route()``
    decorator for how to create the necessary routes.
    """

    def micropath_construct(self, other, kwargs):
        """
        Construct another controller.  This is called on objects which
        have other controller classes mounted on them, in order to
        construct the other controller.  Implementors MUST override
        this method if a controller is mounted.

        :param other: The other controller class to construct.
        :param dict kwargs: Additional keyword arguments passed when
                            setting up the mount point.

        :returns: An instance of the other controller class, properly
                  initialized.  Note that the default implementation
                  raises ``NotImplementedError``.
        """

        raise NotImplementedError(
            'unable to construct class "%s.%s"' %
            (other.__class__.__module__, other.__class__.__name__)
        )
