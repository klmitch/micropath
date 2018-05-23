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

import collections
import functools
import inspect

import six


class WantSignature(object):
    """
    The signature of desired arguments for a function.  This collects
    the sets of keyword arguments that the function wants, and allows
    for the function to be called with only those arguments.  This is
    the core of the dependency injection implementation.
    """

    if six.PY2:
        @staticmethod
        def _getsig(func):
            """
            Obtain a function signature, for Python 2.  This analyzes the
            function argument specification and constructs the
            argument order, required set of arguments, and optional
            set of arguments.

            :param func: The function to analyze.

            :returns: A tuple of five elements.  The first element is
                      a list providing the order of positional
                      arguments.  The second element is a set of the
                      arguments that the function requires be
                      provided.  The third element is a set of the
                      arguments that the function wants, if they are
                      available.  The last two elements are booleans
                      indicating whether the function wants all
                      positional or keyword arguments, respectively.
            """

            # Get the argument specification
            argspec = inspect.getargspec(func)
            order = argspec.args[:]

            # Figure out how many are optional
            if argspec.defaults:
                defcnt = -len(argspec.defaults)
                required = set(order[:defcnt])
                optional = set(order[defcnt:])
            else:
                required = set(order)
                optional = set()

            return (
                order, required, optional,
                argspec.varargs is not None,
                argspec.keywords is not None,
            )
    else:
        @staticmethod
        def _getsig(func):
            """
            Obtain a function signature, for Python 3.  This analyzes the
            function argument specification and constructs the
            argument order, required set of arguments, and optional
            set of arguments.

            :param func: The function to analyze.

            :returns: A tuple of five elements.  The first element is
                      a list providing the order of positional
                      arguments.  The second element is a set of the
                      arguments that the function requires be
                      provided.  The third element is a set of the
                      arguments that the function wants, if they are
                      available.  The last two elements are booleans
                      indicating whether the function wants all
                      positional or keyword arguments, respectively.
            """

            # Initialize the data to return
            order = []
            required = set()
            optional = set()
            all_pos = False
            all_kw = False

            # Get the function signature
            sig = inspect.signature(func, follow_wrapped=False)

            # Process the function signature
            for param in sig.parameters.values():
                # Pick only positional-capable arguments for order
                if param.kind in (
                        param.POSITIONAL_ONLY, param.POSITIONAL_OR_KEYWORD,
                ):
                    order.append(param.name)

                # Pick only keyword-capable arguments for required and
                # optional
                if param.kind in (
                        param.POSITIONAL_OR_KEYWORD, param.KEYWORD_ONLY,
                ):
                    # Presence of a default controls whether it's
                    # required or optional
                    if param.default is param.empty:
                        required.add(param.name)
                    else:
                        optional.add(param.name)

                # Toggle all_pos/all_kw as needed
                if param.kind == param.VAR_POSITIONAL:
                    all_pos = True
                elif param.kind == param.VAR_KEYWORD:
                    all_kw = True

            return (order, required, optional, all_pos, all_kw)

    @classmethod
    def from_func(cls, func, wrapped=None, provides=None,
                  required=None, optional=None):
        """
        Given a function, retrieve its signature.  This will additionally
        cache the signature on the function for future calls.

        :param func: The function to retrieve the signature for.
        :param wrapped: The function being wrapped by ``func``.  This
                        is used if ``func`` is to be a wrapper for
                        another function.
        :param provides: An iterable of function arguments that the
                         wrapper provides to the wrapped function.
                         Only meaningful if ``wrapped`` is provided.
        :param required: An iterable of function arguments that the
                         function requires.  Only meaningful if
                         ``func`` has an all-keywords argument; in
                         this case, the specified arguments are added
                         to the "required" set, and the ``all_kw``
                         value is set to ``False``.
        :param optional: An iterable of function arguments that the
                         function wants if they are available.  Only
                         meaningful if ``func`` has an all-keywords
                         argument; in this case, the specified
                         arguments are added to the "optional" set,
                         and the ``all_kw`` value is set to ``False``.

        :returns: The signature of the specified function.
        :rtype: ``WantSignature``
        """

        # Construct and set the signature
        if not hasattr(func, '_micropath_signature'):
            # First, collect the function signature
            order, func_req, func_opt, all_pos, all_kw = cls._getsig(func)

            # If it's wrapping something, deal with that
            if wrapped is not None:
                wrapped_sig = cls.from_func(wrapped)

                # First, merge in the required and optional
                func_opt = (
                    (func_opt - wrapped_sig.required) |
                    (wrapped_sig.optional - func_req)
                )
                func_req |= wrapped_sig.required

                # Next, discard provided arguments
                provided = set(provides or [])
                func_req -= provided
                func_opt -= provided

            # Handle required and optional
            if all_kw:
                if required is not None:
                    func_req |= set(required)
                    all_kw = False
                if optional is not None:
                    func_opt |= set(optional)
                    all_kw = False

            # Set the function signature
            func._micropath_signature = cls(
                func, order, func_req, func_opt, all_pos, all_kw,
            )

        return func._micropath_signature

    def __init__(self, func, arg_order, required, optional, all_pos, all_kw):
        """
        Initialize a ``WantSignature`` instance.

        :param func: The function the signature is for.  When the
                     signature is invoked, the function will be
                     invoked.
        :param arg_order: A list of the names of arguments, in the
                          order they are defined.
        :type arg_order: ``list`` of ``str``
        :param required: A set of the argument names that must be
                         provided.  Attempts to call the function
                         without one of these arguments will result in
                         an error.
        :type required: ``set`` of ``str``
        :param optional: A set of the argument names that may
                         optionally be provided.  These will typically
                         be arguments for which default values are
                         set.
        :type optional: ``set`` of ``str``
        :param bool all_pos: If ``True``, the function will accept all
                             positional arguments.
        :param bool all_kw: If ``True``, the function will accept all
                            keyword arguments.
        """

        # Make sure there's no overlap
        if required & optional:
            raise ValueError('overlap between required and optional')

        self.func = func
        self.arg_order = arg_order
        self.required = required
        self.optional = optional
        self.all_pos = all_pos
        self.all_kw = all_kw
        self.all_args = required | optional

    def __contains__(self, keyword):
        """
        Used to determine if the function wants a particular keyword
        argument.

        :param str keyword: The name of the keyword argument.

        :returns: A ``True`` value if the signature indicates the
                  function wants the keyword argument (as either
                  required or optional), or ``False`` otherwise.
        :rtype: ``bool``
        """

        return self.all_kw or keyword in self.all_args

    def __call__(self, args, kwargs, additional=None):
        """
        Call the function, passing it the desired arguments and keyword
        arguments.

        :param tuple args: A tuple of positional arguments.  In
                           addition to being passed to the function,
                           this will also skip collecting a value for
                           these arguments from the provided keyword
                           arguments.
        :param dict kwargs: The keyword arguments available to pass to
                            the function.  Only those the function
                            wants, as defined by the signature, will
                            actually be passed.
        :param dict additional: An optional dictionary of additional
                                keyword arguments.  The values in this
                                dictionary will override those
                                provided by ``kwargs``.

        :returns: The return value of calling the function with the
                  specified positional and keyword arguments.
        """

        # Make sure there aren't too many positional arguments
        if not self.all_pos and len(args) > len(self.arg_order):
            raise TypeError(
                'too many positional arguments: got %d, can handle at '
                'most %d' %
                (len(args), len(self.arg_order))
            )

        # Canonicalize additional
        if not additional:
            additional = {}

        # Construct the set of desired keyword arguments
        desired = self.all_args
        if self.all_kw:
            desired |= set(additional) | set(kwargs)
        satisfied = set(self.arg_order[:len(args)])
        desired -= satisfied

        # Construct the keyword arguments
        real_kw = {
            key: additional[key] if key in additional else kwargs[key]
            for key in desired if key in additional or key in kwargs
        }

        # Make sure we got all the required arguments
        missing = self.required - set(real_kw) - satisfied
        if missing:
            raise TypeError(
                'missing required keyword arguments: "%s"' %
                '", "'.join(sorted(missing))
            )

        # Call the function
        return self.func(*args, **real_kw)


class InjectorCleanup(object):
    """
    A context manager for cleaning up keys added to an ``Injector``.
    This is used to mitigate reference loops that could cause problems
    for the Python garbage collector.
    """

    def __init__(self, injector):
        """
        Initialize an ``InjectorCleanup`` instance.

        :param injector: The injector to clean up.
        :type injector: ``Injector``
        """

        self.injector = injector
        self.keep = None

    def __enter__(self):
        """
        Enter the context manager.  This copies the set of existing keys
        for later cleanup operations.

        :returns: The injector.
        :rtype: ``Injector``
        """

        # Must be None
        assert self.keep is None

        # Copy the current set of keys
        self.keep = set(self.injector._keys)

        return self.injector

    def __exit__(self, exc_type, exc_value, exc_tb):
        """
        Exit the context manager.  This deletes all keys added to the
        injector since the context manager was entered.  The
        exception, if any, is not handled.

        :param exc_type: The type of the exception that was raised, or
                         ``None``.
        :param exc_value: The exception that was raised, or ``None``.
        :param exc_tb: The traceback of the exception that was raised,
                       or ``None``.

        :returns: A ``None`` value, to indicate that the exception was
                  not handled.
        """

        # Must not be None
        assert self.keep is not None

        # Delete the added keys
        for key in self.injector._keys - self.keep:
            del self.injector[key]

        # Reset keep
        self.keep = None

        return None


class Injector(collections.MutableMapping):
    """
    A mutable mapping that provides the collection of arguments that
    are available to be passed to a function.  This is used in
    conjunction with the ``WantSignature`` class for dependency
    injection.
    """

    def __init__(self):
        """
        Initialize an ``Injector`` instance.
        """

        # Set up the maps and the key set
        self._available = {}  # values
        self._deferred = {}  # callables generating values
        self._keys = set()  # efficiency enhancement containing keys

    def __len__(self):
        """
        Return the number of items in the mapping.

        :returns: The number of items in the mapping.
        :rtype: ``int``
        """

        return len(self._keys)

    def __iter__(self):
        """
        Iterate over the keys in the mapping.

        :returns: An iterator over the keys in the mapping.
        """

        return iter(self._keys)

    def __getitem__(self, key):
        """
        Retrieve the value of an item.  If the value has not been set, but
        a deferred callable for it has, that deferred callable will be
        called and the value set, prior to returning it.

        :param key: The key of the item to retrieve.

        :returns: The value associated with that key.
        """

        # Handle the KeyError case first
        if key not in self._keys:
            raise KeyError(key)

        # If it's not available, we'll need to call the deferred
        # action
        if key not in self._available:
            self._available[key] = self(self._deferred[key])

        return self._available[key]

    def __setitem__(self, key, value):
        """
        Set the value of an item.  This will mask any deferred callable
        that has been set for the same key.

        :param key: The key of the item to set.
        :param value: The value to associate with the key.
        """

        self._available[key] = value
        self._keys.add(key)

    def __delitem__(self, key):
        """
        Delete the value of an item.  This also discards any deferred
        callable that has been set for the key.

        :param key: The key of the item to delete.
        """

        # Handle the KeyError case first
        if key not in self._keys:
            raise KeyError(key)

        # Pop it off
        self._available.pop(key, None)
        self._deferred.pop(key, None)
        self._keys.discard(key)

    def __call__(self, *args, **kwargs):
        """
        Call a function, injecting the keyword arguments desired by the
        function from the keys defined in this mapping.  The first
        positional parameter must be the function to invoke.
        Additional positional arguments are passed directly to the
        function, and additional keyword arguments override values
        from this mapping.  This is the entrypoint for dependency
        injection.
        """

        if len(args) < 1:
            raise TypeError('call requires at least one positional argument')

        # Split the function and arguments
        func = args[0]
        args = args[1:]

        # Unwrap class and instance methods
        if inspect.ismethod(func):
            obj = six.get_method_self(func)
            func = six.get_method_function(func)

            # Update the args
            args = (obj,) + args

        # Get the function's injection signature
        sig = WantSignature.from_func(func)

        # Call the function
        return sig(args, self, kwargs)

    def set_deferred(self, key, func):
        """
        Set a deferred callable for a key.  This may be used when a value
        for a key should only be generated if the function being
        called actually wants the value, usually because generating
        the value is somewhat expensive.

        :param key: The key the value should be associated with.
        :param func: A callable that will generate the value to
                     associate with the key.
        """

        self._deferred[key] = func

    def cleanup(self):
        """
        Returns a context manager that ensures that keys added during the
        execution of the ``with`` statement are deleted at the end.
        This is used to help mitigate reference loops by explicitly
        breaking them.

        :returns: A context manager for cleaning up the injector.
        :rtype: ``InjectorCleanup``
        """

        return InjectorCleanup(self)


def inject(required=None, optional=None):
    """
    A function decorator that allows dependency injection to be
    tailored.  In most cases, it is not necessary to use this
    decorator; it may be used when a function takes all keyword
    arguments--i.e., a ``**kwargs`` or similar argument is
    present--but the developer wishes to restrict the set of
    injectible arguments.

    :param required: An iterable of function arguments that the
                     function requires.
    :param optional: An iterable of function arguments that the
                     function wants if they are available.

    :returns: A function decorator that sets the dependency injection
              metadata of the function as desired.
    """

    # The actual decorator; just calls from_func() with appropriate
    # arguments
    def decorator(func):
        WantSignature.from_func(func, required=required, optional=optional)
        return func

    return decorator


# Sentinel to indicate required/optional not explicitly provided
_unset = object()


def wraps(wrapped, assigned=functools.WRAPPER_ASSIGNMENTS,
          updated=functools.WRAPPER_UPDATES, provides=None,
          required=_unset, optional=_unset):
    """
    A function decorator for wrapping decorators.  This works just
    like ``six.wraps()`` (which in turn works just like
    ``functools.wraps()``), but additionally manages dependency
    injection metadata, allowing decorators to request data
    independent of the function they wrap.

    :param wrapped: The function that is being wrapped.
    :param assigned: A tuple naming the attributes assigned directly
                     from the wrapped function to the wrapper
                     function.  Defaults to
                     ``functools.WRAPPER_ASSIGNMENTS``.
    :param updated: A tuple naming the attributes of the wrapper that
                    are updated with the corresponding attribute from
                    the wrapped function.  Defaults to
                    ``functools.WRAPPER_UPDATES``.
    :param provides: An iterable of function arguments that the
                     wrapper provides to the wrapped function.
    :param required: An iterable of function arguments that the
                     function requires.  Only meaningful if ``func``
                     has an all-keywords argument; in this case, the
                     specified arguments are added to the "required"
                     set, and the ``all_kw`` value is set to
                     ``False``.  Note that by default, ``required`` is
                     set to the empty list; pass ``None`` for both
                     ``required`` and ``optional`` to pass all
                     injectible keyword arguments to the wrapper.
    :param optional: An iterable of function arguments that the
                     function wants if they are available.  Only
                     meaningful if ``func`` has an all-keywords
                     argument; in this case, the specified arguments
                     are added to the "optional" set, and the
                     ``all_kw`` value is set to ``False``.  Note that
                     by default, ``optional`` is set to the empty
                     list; pass ``None`` for both ``required`` and
                     ``optional`` to pass all injectible keyword
                     arguments to the wrapper.

    :returns: A function decorator that properly updates the
              attributes of the wrapper function, while also setting
              the dependency injection metadata of the wrapper
              function as desired.
    """

    # The actual decorator
    def decorator(func):
        # Generate the signature first
        sig = WantSignature.from_func(
            func, wrapped, provides,
            [] if required is _unset else required,
            [] if optional is _unset else optional,
        )

        # Next, wrap it
        func = six.wraps(wrapped, assigned, updated)(func)

        # The wrapper may override the signature, so reset it
        func._micropath_signature = sig

        return func

    return decorator


def call_wrapped(func, args, kwargs):
    """
    Call a wrapped function with appropriate dependency injection.
    This is for use by decorators that wrap a function that will be
    called via dependency injection, and ensures that the function is
    called only with the desired keyword arguments.

    :param func: The wrapped function.
    :param args: A tuple of positional arguments to pass to the
                 function.
    :param kwargs: A dictionary of keyword arguments to pass to the
                   function.  If the decorator provides arguments
                   (uses the ``micropath.wraps()`` decorator with the
                   ``provides`` argument), those argument values must
                   be present in ``kwargs``.

    :returns: The result of calling the wrapped function.
    """

    # Get the function's injection signature
    sig = WantSignature.from_func(func)

    # Call the function
    return sig(args, kwargs)


def wants(func, keyword):
    """
    Determine if a function wants a particular keyword argument.

    :param func: The function.
    :param str keyword: The keyword argument.

    :returns: A ``True`` value if the function wants the keyword
              argument, or ``False`` otherwise.
    :rtype: ``bool``
    """

    # Get the function's injection signature
    sig = WantSignature.from_func(func)

    # See if it wants the argument
    return keyword in sig
