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

import inspect

import six
import webob

from micropath import elements
from micropath import injector


class Request(webob.Request):
    """
    A subclass of ``webob.Request`` containing additional support used
    by the ``micropath`` framework.  In particular, the ``injector``
    attribute contains the dependency injector used by ``micropath``
    to invoke handler methods, and the ``base_path`` attribute is the
    value of the ``SCRIPT_NAME`` WSGI environment variable at the time
    the ``Request`` was constructed.  (This latter attribute may be
    used to construct absolute paths to other ``micropath`` handlers.)
    In addition, the ``url_for()`` method is capable of constructing a
    URL for any given controller method.
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize a ``Request`` instance.  Parameters are passed to the
        underlying ``webob.Request``.  This method also adds the
        ``micropath.base_path`` key to the WSGI environment (use the
        ``base_path`` attribute to access it).
        """

        super(Request, self).__init__(*args, **kwargs)

        # Save the base path for later URL computation
        self.environ['micropath.base_path'] = self.script_name

    def url_for(self, *args, **kwargs):
        """
        Construct the absolute URL for a given handler method.  The
        handler method should be passed as the only positional
        parameter, and keyword parameters should be passed to provide
        values for the bindings (which will be passed to the
        ``micropath.elements.Binding.format()`` method to be converted
        into URL path elements).

        :returns: An absolute URL corresponding to the handler method.
                  Note that it is not guaranteed that that handler
                  method will be called by accessing the URL; that
                  depends on the HTTP methods routed to the handler
                  method.
        :rtype: ``str``
        """

        # Sanity-check the arguments
        if len(args) != 1:
            raise TypeError(
                'url_for() requires exactly 1 positional argument; %d given' %
                len(args),
            )
        elif (not callable(args[0]) or
              getattr(args[0], '_micropath_elem', None) is None):
            raise ValueError('unable to construct URL for %r' % args[0])

        # Get the controller and element
        controller = six.get_method_self(args[0])
        elem = args[0]._micropath_elem

        # Make sure it is a controller instance and not a class
        if inspect.isclass(controller):
            raise ValueError('unable to construct URL for class method')

        # Begin walking up the controller/element tree
        path_elems = []
        while controller:
            while elem:
                if isinstance(elem, elements.Path):
                    # Just add the element's ident
                    path_elems.append(elem.ident)
                elif isinstance(elem, elements.Binding):
                    # Make sure we have a value
                    if elem.ident not in kwargs:
                        raise ValueError(
                            'missing value for binding "%s"' % elem.ident,
                        )

                    # Format the value
                    path_elems.append(elem.format(
                        controller, kwargs[elem.ident],
                    ))
                else:
                    assert isinstance(elem, elements.Root)

                # Walk up to the element's parent
                elem = elem.parent

            # Walk up the controller chain
            elem = getattr(controller, '_micropath_elem', None)
            controller = getattr(controller, '_micropath_parent', None)

        # Construct the path
        return '%s%s/%s' % (
            self.host_url, self.base_path, '/'.join(reversed(path_elems)),
        )

    @property
    def injector(self):
        """
        Retrieve the dependency injector from the WSGI environment.
        """

        if 'micropath.injector' not in self.environ:
            self.environ['micropath.injector'] = injector.Injector()

        return self.environ['micropath.injector']

    @property
    def base_path(self):
        """
        Retrieve the base path.  This may be used to construct full URLs.
        The base path is the value of the ``SCRIPT_NAME`` WSGI
        environment variable at the time the ``Request`` instance is
        constructed.
        """

        return self.environ.get('micropath.base_path')
