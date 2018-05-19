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

import webob

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
