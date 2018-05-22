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

from micropath import request


def safestr(value):
    """
    Turns ``None`` into the string "<None>".

    :param str value: The value to safely stringify.

    :returns: The stringified version of ``value``.
    """

    return value or '<None>'


def invoke(controller, *args, **kwargs):
    """
    Invoke a controller.  A request is constructed from the positional
    and keyword arguments.

    :param controller: An instance of the controller to invoke.
    :type controller: ``micropath.controller.Controller``

    :returns: A tuple of three elements.  The first element is the
              status string; the second element is a dictionary of
              headers; and the third is the textual contents of the
              body.
    """

    # First, construct a request
    req = request.Request.blank(*args, **kwargs)

    # Call the controller
    status, header_list, body_iter = req.call_application(controller)

    # Construct the header dictionary
    headers = {
        name.lower(): value for name, value in header_list
    }

    # Construct the body
    body = b''.join(body_iter)
    if hasattr(body_iter, 'close'):
        body_iter.close()

    return status, headers, body
