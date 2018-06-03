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

import sys
import traceback
from wsgiref import simple_server

import six
import webob.dec
import webob.exc

from micropath import elements
from micropath import injector
from micropath import request


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

        # Collect delegations
        delegations = {}

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

            # Mount the delegation to the root
            if isinstance(value, elements.Delegation):
                if value.element is None:
                    root.mount(value)
                else:
                    root.add_elem(value.element, ident)

                # Add it to the set of delegations
                delegations[ident] = value
                continue

            # Deal with handlers
            if getattr(value, '_micropath_handler', False):
                # If it doesn't have an elem, set it to the root
                if getattr(value, '_micropath_elem', None) is None:
                    value._micropath_elem = root

        # Add the root and handlers list to the namespace
        namespace.update(
            _micropath_root=root,
            _micropath_delegations=[
                delegation for _name, delegation in
                sorted(delegations.items(), key=lambda x: x[0])
            ],
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

    This class has some attributes that subclasses may set if desired,
    to control behavior.  Those class attributes are as follows:

    * ``micropath_request`` - The class to use for representing a
        request.  This must be a subclass of ``micropath.Request``.
    * ``micropath_methods`` - The ``micropath`` framework has a
        default implementation for the "OPTIONS" HTTP method.  This
        class attribute should contain a set of the HTTP methods that
        are recognized if a default route is available (one for which
        no methods have been passed to the ``@micropath.route()``
        decorator).  The default contains "HEAD", "GET", "PUT",
        "POST", "DELETE", and of course "OPTIONS".
    * ``micropath_debug`` - A class attribute that is set to
        ``False``.  This may be shadowed by an instance attribute of
        the same name to enable debugging responses; this will include
        traceback and debugging information in the 500 error generated
        if the ``micropath_server_error()`` hook method raises an
        exception.  The default implementations of
        ``micropath_request_error()`` and ``micropath_server_error()``
        also include traceback and debugging information if this
        attribute is ``True``.  WARNING: THIS ATTRIBUTE MUST NOT BE
        SET TO ``True`` ON PRODUCTION SERVERS!  Exception information
        can leak security-sensitive data to callers.
    * ``micropath_request_attrs`` - A dictionary of request attributes
        that may be injected into handler methods.  The keys of this
        dictionary are the parameter names the handler methods may
        request, and the values are the names of the attribute of the
        request.  A value of ``None`` indicates that the attribute has
        the same name as the parameter name.  The default value allows
        all request attributes to be injected; subclasses that
        override this attribute may wish to copy the value from
        ``micropath.Controller`` and then update it to list additional
        attributes.

    In addition to the class attributes listed above, subclasses may
    also override several methods to control behavior.  The methods
    that may be overridden are as follows:

    * ``micropath_construct()`` - Called when a mounted class is
        traversed.  The default implementation constructs the mounted
        class with only the passed keyword arguments, so if using
        ``micropath.mount()`` and the controller classes require other
        arguments (e.g., configuration), the class must implement this
        method.  Since ``micropath`` does not provide any constraints
        on your controller class's ``__init__()`` method, the
        intention of this hook method is to allow the mounted class to
        be properly configured.  For instance, if you load a
        configuration file and then pass it to the ``config``
        parameter of your root controller class's ``__init__()``
        method, you should implement ``micropath_construct()`` to
        construct the other class with that same configuration.
    * ``micropath_prepare_injector()`` - Called immediately after the
        dependency injector has been initialized.  This can be used to
        add additional fields to the dependency injector.  Only the
        implementation in the root ``Controller`` subclass is useful.
    * ``micropath_server_error()`` - Called if a handler method or the
        injector raises any exception that is not
        ``webob.exc.HTTPException``.  The default implementation
        returns a bare ``webob.exc.HTTPInternalServerError``, which
        causes a 500 error to be returned to the HTTP client.  This
        must be implemented in each ``Controller`` subclass, so if
        customizing this hook, it is recommended to create a base
        class with the desired implementation, then subclass that.
    * ``micropath_request_error()`` - Called if a handler method
        requests an attribute of the request object, but an error
        occurs while accessing that attribute.  This typically
        indicates a format error with the requested resource, such as
        invalid JSON data when attempting to access ``json_body``.  As
        such, the default implementation returns a bare
        ``webob.exc.HTTPBadRequest``, which causes a 400 error to be
        returned to the HTTP client.  Only the implementation in the
        root ``Controller`` subclass is useful.  Also note that the
        return value of this hook method must be a subclass of
        ``Exception``.
    * ``micropath_not_found()`` - Called if the path could not be
        resolved.  Note that this will not be called for a given
        request if the handler function for that URL and HTTP method
        includes the ``path_info`` parameter.  This must be
        implemented in each ``Controller`` subclass, so if customizing
        this hook, it is recommended to create a base class with the
        desired implementation, then subclass that.
    * ``micropath_not_implemented()`` - Called if the HTTP method is
        not implemented.  This must be implemented in each
        ``Controller`` subclass, so if customizing this hook, it is
        recommended to create a base class with the desired
        implementation, then subclass that.
    * ``micropath_options()`` - Called if the HTTP method is "OPTIONS"
        and the method isn't routed to a handler.  This method must
        create a response that includes the "Allow" header with a
        comma-separated list of methods.  This must be implemented in
        each ``Controller`` subclass, so if customizing this hook, it
        is recommended to create a base class with the desired
        implementation, then subclass that.

    The ``Controller`` base class also defines an ``__init__()``
    method that all subclasses must ensure is called with no
    arguments.  This base ``__init__()`` method instantiates the
    mounted controllers, in order to ensure that there are no race
    conditions during request processing in the face of threaded WSGI
    servers.  This means that the ``micropath`` framework is itself
    thread-safe, without needing to use any threading primitives.

    Finally, a convenience ``micropath_run()`` method is provided for
    testing purposes (it should not be used on production systems).
    This method serves the WSGI application at a specified host and
    port.
    """

    # Set the default class to use for requests
    micropath_request = request.Request

    # The set of methods to be considered implemented if a default
    # route was added to a handler
    micropath_methods = set([
        'HEAD', 'GET', 'PUT', 'POST', 'DELETE', 'OPTIONS'
    ])

    # Controls debugging.  THIS ATTRIBUTE MUST NOT BE True ON
    # PRODUCTION SERVERS!
    micropath_debug = False

    # Set the default set of request attributes to make injectable
    micropath_request_attrs = {
        'get': 'GET',
        'post': 'POST',
        'accept': None,
        'accept_charset': None,
        'accept_encoding': None,
        'accept_language': None,
        'application_url': None,
        'authorization': None,
        'base_path': None,
        'body': None,
        'body_file': None,
        'body_file_raw': None,
        'body_file_seekable': None,
        'cache_control': None,
        'charset': None,
        'client_addr': None,
        'content_length': None,
        'content_type': None,
        'cookies': None,
        'date': None,
        'domain': None,
        'environ': None,
        'headers': None,
        'host': None,
        'host_port': None,
        'host_url': None,
        'http_version': None,
        'if_match': None,
        'if_modified_since': None,
        'if_none_match': None,
        'if_range': None,
        'if_unmodified_since': None,
        'injector': None,
        'is_body_readable': None,
        'is_body_seekable': None,
        'is_xhr': None,
        'json': None,
        'json_body': None,
        'max_forwards': None,
        'method': None,
        'params': None,
        'path': None,
        'path_info': None,
        'path_qs': None,
        'path_url': None,
        'pragma': None,
        'query_string': None,
        'range': None,
        'referer': None,
        'referrer': None,
        'remote_addr': None,
        'remote_user': None,
        'scheme': None,
        'script_name': None,
        'server_name': None,
        'server_port': None,
        'text': None,
        'url': None,
        'url_encoding': None,
        'urlargs': None,
        'urlvars': None,
        'user_agent': None,
    }

    def __init__(self):
        """
        Initialize a ``Controller`` instance.  Subclasses must call the
        superclass method to properly initialize the controller.
        """

        # Initialize delegations; this ensures that all subordinate
        # controllers are initialized at the time the root controller
        # is, thus avoiding any threading issues within the
        # Delegations.get() logic
        for deleg in self._micropath_delegations:
            deleg.get(self)

    def __call__(self, environ, start_response):
        """
        Contains the implementation of the WSGI application which is the
        heart of the ``micropath`` framework.  This allows instances
        of subclasses of ``Controller`` to be used as WSGI
        applications.

        :param dict environ: The WSGI environment.
        :param start_response: The callable used to start the
                               response.

        :returns: The return value of invoking the response WSGI
                  application, as returned by the handler methods.  If
                  no handler method is available, an appropriate error
                  will be generated to indicate that the path doesn't
                  exist (404) or the method is unacceptable (501).
        """

        # Note: The contents of this method are mostly copied from the
        # __call__() method of webob.dec.wsgify

        # First, construct the request and set the default response
        req = self.micropath_request(environ)
        req.response = req.ResponseClass()

        # Next, walk the path tree and invoke the handler; we use the
        # injector cleanup context manager to explicitly break
        # reference loops after we've dispatched to the handler method
        with req.injector.cleanup() as injector:
            try:
                # Add anything from the request's urlvars
                injector.update(req.urlvars)

                # Populate the request and root_controller fields of
                # the injector
                injector['request'] = req
                injector['root_controller'] = self

                # Add deferred accessors for all the other fields
                def defer(key):
                    # Can't use operator.attrgetter because we need
                    # the parameter to be named "request"
                    def get(request):
                        try:
                            return getattr(request, key)
                        except Exception:
                            raise self.micropath_request_error(
                                request, key, sys.exc_info(),
                            )
                    return get
                for key, mapped in self.micropath_request_attrs.items():
                    injector.set_deferred(key, defer(mapped or key))

                # Hook for setting up additional injection settings
                self.micropath_prepare_injector(req, injector)

                resp = self._micropath_dispatch(req, injector)
            except webob.exc.HTTPException as exc:
                resp = exc
            except Exception:
                # Some other error occurred; we'll turn it into an
                # internal server error
                try:
                    resp = self.micropath_server_error(req, sys.exc_info())
                except Exception:
                    # An exception could be raised by
                    # micropath_server_error(); this clause acts as an
                    # absolute last resort to ensure that no exception
                    # makes it all the way up the stack.  Begin by
                    # formulating the detail for debugging purposes
                    detail = None
                    if self.micropath_debug:
                        # Debugging detail requested; format traceback
                        detail = traceback.format_exc()

                    # Construct the exception
                    resp = webob.exc.HTTPInternalServerError(detail)

        # Use the default response if none was returned
        if resp is None:
            resp = req.response

        # Convert text and bytes
        if isinstance(resp, six.text_type):
            resp = resp.encode(req.charset)
        if isinstance(resp, bytes):
            body = resp
            resp = req.response
            resp.write(body)

        # Merge the cookies
        if resp is not req.response:
            resp = req.response.merge_cookies(resp)

        # Return the response
        return resp(environ, start_response)

    def _micropath_dispatch(self, req, inj):
        """
        Walk the element tree based on the URL path in the request.  This
        method is used to locate the correct handler to invoke for a
        given request, or to invoke a proper delegation to handle the
        next part of the request URL.

        :param req: The request being processed.
        :type req: ``micropath.Request``
        :param inj: The injector.  This will have bindings added to
                    it, and will be used to invoke the handler method.
        :type inj: ``micropath.injector.Injector``

        :returns: The result of invoking the handler method.
        """

        # Resolve the path to a Path or Binding
        elem, path_info_required = self._micropath_resolve(req, inj)

        # Get the matching function and delegation
        func, delegation = self._micropath_delegation(req, elem)

        # First, is there a function?
        if (func and
                (not path_info_required or injector.wants(func, 'path_info'))):
            return inj(func, self)

        # OK, delegate if needed
        if delegation:
            # Get the object being delegated to
            obj = delegation.get(self)

            # Dispatch to it
            return obj._micropath_dispatch(req, inj)

        # We couldn't find an implementation...
        if path_info_required or not elem.methods:
            # Couldn't find the path; we'll return a 404
            return self.micropath_not_found(req, req.path_info)
        elif elem.methods and req.method == 'OPTIONS':
            meths = self._micropath_methods(elem)

            # Generate and return the OPTIONS response
            return self.micropath_options(req, list(sorted(meths)))

        # Couldn't find an implementation for the method
        return self.micropath_not_implemented(req, req.method)

    def _micropath_resolve(self, req, inj):
        """
        Resolve the request URL path to a specific path element.  This
        will set up injections for any variable bindings, as well as
        setting the variable bindings on the request's ``urlvars``
        dictionary.

        :param req: The request being processed.
        :type req: ``micropath.Request``
        :param inj: The injector.  This will have bindings added to
                    it.
        :type inj: ``micropath.injector.Injector``

        :returns: A tuple of the found path element (either
                  ``micropath.elements.Path`` or
                  ``micropath.elements.Binding``) and a boolean
                  indicating whether the ``path_info`` of the request
                  has been exhausted--if ``True``, the implementing
                  function must want the ``path_info`` attribute, or a
                  404 will be generated.
        """

        # Must the handler have path_info?
        path_info_required = True

        # Start at the controller's root
        elem = self._micropath_root
        path_elem = req.path_info_peek()
        while path_elem:
            # If it's a static path, we'll go down that branch
            if path_elem in elem.paths:
                elem = elem.paths[path_elem]
            elif elem.bindings is not None:
                try:
                    value = elem.bindings.validate(self, inj, path_elem)
                except elements.SkipBinding:
                    break

                # Save it into the injector and the urlvars
                if elem.bindings.ident not in inj:
                    # Only add to the injector if there are no
                    # conflicts
                    inj[elem.bindings.ident] = value
                req.urlvars[elem.bindings.ident] = value

                # Set the next element
                elem = elem.bindings
            else:
                break

            # OK, pop off the path element and set up for the next one
            req.path_info_pop()
            path_elem = req.path_info_peek()
        else:
            # Ran off the end of the path_info
            path_info_required = False

        return elem, path_info_required

    def _micropath_delegation(self, req, elem):
        """
        Determine what function or mount point to delegate the request to.

        :param req: The request being processed.
        :type req: ``micropath.Request``

        :param elem: The path element at which to resolve the
                     delegation.
        :type elem: ``micropath.elements.Element``

        :returns: A tuple of the function and a delegation.  Either or
                  both may be ``None``.  If the delegation is not
                  ``None``, it will be an instance of
                  ``micropath.elements.Delegation``.
        """

        # Pick out the Method instance
        meth = elem.methods.get(
            'GET' if req.method == 'HEAD' else req.method,
            elem.methods.get(None),
        )

        return (
            meth.func if meth else None,
            (meth.delegation or elem.delegation) if meth else elem.delegation,
        )

    def _micropath_methods(self, elem):
        """
        Determine the methods available at a particular point in the URL
        hierarchy.

        :param elem: The path element.
        :type elem: ``micropath.elements.Element``

        :returns: A set of the HTTP methods that are implemented at
                  this point of the URL hierarchy.
        :rtype: ``set`` of ``str``
        """

        # First, get the set of methods we see in elem.methods
        meths = set(m for m in elem.methods if m is not None)

        # Next, add the micropath_methods if None is in
        # elem.methods
        if None in elem.methods:
            meths |= self.micropath_methods

        # Now, add the fixed options: HEAD (if GET is present)
        # and, of course, OPTIONS
        if 'GET' in meths:
            meths.add('HEAD')
        meths.add('OPTIONS')

        return meths

    def micropath_construct(self, other, kwargs):
        """
        Construct another controller.  This is called on objects which
        have other controller classes mounted on them, in order to
        construct the other controller.

        :param other: The other controller class to construct.
        :param dict kwargs: Additional keyword arguments passed when
                            setting up the mount point.

        :returns: An instance of the other controller class, properly
                  initialized.
        """

        return other(**kwargs)

    def micropath_prepare_injector(self, request, injector):
        """
        A hook method for injector preparation.  This allows subclasses to
        add things to the injector if needed.

        :param request: The request being processed.
        :type request: ``micropath.Request``
        :param injector: The injector being prepared.  Implementations
                         can assign values using dictionary syntax, or
                         may set functions that will be called with
                         appropriate arguments (using dependency
                         injection) using the
                         ``injector.set_deferred()`` method.  The
                         ``injector.set_deferred()`` method takes the
                         name of the parameter and the implementing
                         function as its two required arguments, and
                         the function is expected to return the value
                         that will be injected as an argument.
        :type injector: ``micropath.injector.Injector``
        """

        pass  # pragma: no cover

    def micropath_server_error(self, request, cause):
        """
        A hook method for handling the case that an exception that was not
        a ``webob.exc.HTTPException`` was raised during request
        processing.

        :param request: The request that caused the error to be
                        raised.
        :param cause: The exception tuple for the exception that
                      caused this method to be called.  This will be
                      the tuple from ``sys.exc_info()``.

        :returns: An appropriate response.  The default implementation
                  returns a bare
                  ``webob.exc.HTTPInternalServerError``, including
                  traceback information only if ``micropath_debug`` is
                  set to ``True``.  NOTE THAT, FOR SECURITY REASONS,
                  THE TRACEBACK SHOULD *NOT* BE INCLUDED ON PRODUCTION
                  SYSTEMS: THIS INFORMATION MAY INCLUDE SENSITIVE
                  DATA, SUCH AS PATHS.
        """

        # Formulate the detail for debugging purposes
        detail = None
        if self.micropath_debug:
            # Debugging detail requested; format traceback
            detail = ''.join(traceback.format_exception(*cause))

        # Construct and return the exception
        return webob.exc.HTTPInternalServerError(detail)

    def micropath_request_error(self, request, attr, cause):
        """
        A hook method for handling the case that an exception that was not
        a ``webob.exc.HTTPException`` was raised while injecting a
        request attribute.  This might occur if a JSON payload was not
        valid JSON, for instance.

        :param request: The request that caused the error to be
                        raised.
        :param str attr: The name of the attribute that could not be
                         accessed.
        :param cause: The exception tuple for the exception that
                      caused this method to be called.  This will be
                      the tuple from ``sys.exc_info()``.

        :returns: An appropriate response.  The default implementation
                  returns a bare ``webob.exc.HTTPBadRequest``,
                  including traceback information only if
                  ``micropath_debug`` is set to ``True``.  NOTE THAT,
                  FOR SECURITY REASONS, THE TRACEBACK SHOULD *NOT* BE
                  INCLUDED ON PRODUCTION SYSTEMS: THIS INFORMATION MAY
                  INCLUDE SENSITIVE DATA, SUCH AS PATHS.  Also note
                  that the return value of this function MUST be an
                  object extending ``Exception``, such as
                  ``webob.exc.HTTPBadRequest``; the value will be
                  passed to ``raise``.
        """

        # Formulate the detail for debugging purposes
        detail = None
        if self.micropath_debug:
            # Debugging detail requested; format traceback
            detail = 'Accessing request attribute "%s":\n%s' % (
                attr, ''.join(traceback.format_exception(*cause)),
            )

        # Construct and return the exception
        return webob.exc.HTTPBadRequest(detail)

    def micropath_not_found(self, request, path_info):
        """
        A hook method for the case that the path could not be fully
        resolved.

        :param request: The request that caused the error to be
                        encountered.
        :param str path_info: The remaining portions of the URL path
                              that could not be resolved.

        :returns: An appropriate response.  The default implementation
                  returns a bare ``webob.exc.HTTPNotfound``.
        """

        return webob.exc.HTTPNotFound()

    def micropath_not_implemented(self, request, method):
        """
        A hook method for the case that the request method is not
        implemented.

        :param request: The request that caused the error to be
                        encountered.
        :param str method: The HTTP method that was not implemented.

        :returns: An appropriate response.  The default implementation
                  returns a bare ``webob.exc.HTTPNotImplemented``.
        """

        return webob.exc.HTTPNotImplemented()

    def micropath_options(self, request, methods):
        """
        A hook method for implementing the response to the OPTIONS HTTP
        method.

        :param request: The request that caused the default OPTIONS
                        handler to be invoked.
        :param methods: A sorted list of HTTP methods.  This should be
                        turned into a comma-separated list and placed
                        in the response's "Allow" header.

        :returns: An appropriate response.  The default implementation
                  returns a ``webob.exc.HTTPNoContent`` with the
                  "Allow" header set to the comma-separated list of
                  allowed HTTP methods.
        """

        return webob.exc.HTTPNoContent(headers={'Allow': ','.join(methods)})

    def micropath_run(self, host='127.0.0.1', port=8000):
        """
        Serve the application.  This makes use of the Python standard
        library ``wsgiref`` package's ``simple_server`` to present the
        application defined in this controller as a WSGI server.

        Note: It is NOT RECOMMENDED to use this method to serve an
        application for production purposes.  No attempt is made to
        handle threading, error handling, SSL, or a host of other
        issues that real, production-ready HTTP and WSGI servers
        handle.  This method is provided for testing purposes only.

        :param str host: The IP address for the server to listen on.
                         Defaults to "127.0.0.1", meaning to listen on
                         the loopback interface (aka, "localhost".)
        :param int port: The port for the server to listen on.
                         Defaults to 8000.
        """

        server = simple_server.make_server(host, port, self)
        server.serve_forever()
