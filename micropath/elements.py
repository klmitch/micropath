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

import abc
import functools

import six

from micropath import injector


@six.add_metaclass(abc.ABCMeta)
class Element(object):
    """
    Represent an abstract path element.  This can either be a constant
    component (``Path``); a variable component (``Binding``); or an
    HTTP method (``Method``).
    """

    def __init__(self, ident, parent=None):
        """
        Initialize an ``Element`` instance.

        :param str ident: The identifier for the component.  For
                          constant components, this will be the
                          expected value of the component; for
                          variable components, this will be the name
                          of the variable to contain the value.
        :param parent: The parent element.  Defaults to ``None``,
                       indicating the root of the element tree.
        :type parent: ``Element``
        """

        # Save the parameter
        self.ident = ident
        self.parent = parent

        # Set up subordinate lists
        self.paths = {}
        self.bindings = None
        self.methods = {}

        # For delegation to other controllers
        self.delegation = None

    @abc.abstractmethod
    def set_ident(self, ident):
        """
        Set the element identifier.  This can be used in the case that the
        identifier was not set at construction time.  Subclasses must
        call the superclass abstract method to set the identifier,
        then must update the subordinate lists in the parent object,
        if a parent exists.

        :param str ident: The identifier for the component.  For
                          constant components, this will be the
                          expected value of the component; for
                          variable components, this will be the name
                          of the variable to contain the value.

        :raises ValueError:
            The element identifier has already been set.
        """

        # Elements must be immutable
        if self.ident:
            raise ValueError('ident has already been set to "%s"' % self.ident)

        # Set the identifier
        self.ident = ident

    def path(self, ident=None):
        """
        Construct a new subordinate ``Path`` element.

        :param str ident: The identifier for the component.  For
                          constant components, this will be the
                          expected value of the component.  May be
                          ``None`` (the default) to indicate that the
                          metaclass should set the value from the name
                          of the class variable to which the element
                          is assigned.

        :returns: The newly constructed element.
        :rtype: ``Path``
        """

        # Construct the new path
        elem = Path(ident, parent=self)

        # If it has an identifier, add it to the lists
        if elem.ident:
            if elem.ident in self.paths:
                raise ValueError(
                    'Path element for "%s" already exists' % elem.ident,
                )
            self.paths[elem.ident] = elem

        return elem

    def bind(self, ident=None):
        """
        Construct a new subordinate ``Binding`` element.

        :param str ident: The identifier for the component.  For
                          variable components, this will be the name
                          of the variable to contain the value.  May
                          be ``None`` (the default) to indicate that
                          the metaclass should set the value from the
                          name of the class variable to which the
                          element is assigned.

        :returns: The newly constructed element.
        :rtype: ``Binding``
        """

        # Construct the new binding
        elem = Binding(ident, parent=self)

        # If it has an identifier, add it to the lists
        if elem.ident:
            if self.bindings is not None:
                raise ValueError(
                    'Binding element for "%s" already exists' % elem.ident,
                )
            self.bindings = elem

        return elem

    def route(self, *methods):
        """
        Method decorator to route HTTP methods to a method.  Called with
        an optional list of method strings (which will be
        canonicalized to uppercase).  If no methods are specified, all
        otherwise undefined methods will be routed to the decorated
        method.  This decorator is designed to work both with and
        without arguments--that is, ``@obj.route`` is equivalent to
        ``@obj.route()``.

        :returns: Either the appropriately decorated method, or a
                  decorator for a method.
        """

        def decorator(func):
            # Construct the new Method objects
            if methods:
                for meth_str in methods:
                    if meth_str in self.methods:
                        continue
                    meth = Method(meth_str, func, parent=self)
                    self.methods[meth.ident] = meth
            else:
                meth = Method(None, func, parent=self)
                self.methods[meth.ident] = meth

            # Mark the function as a handler and save its element
            func._micropath_handler = True
            func._micropath_elem = self

            # Pre-compute its want signature
            injector.WantSignature.from_func(func)

            return func

        # Check if methods consists of a single callable element
        if len(methods) == 1 and callable(methods[0]):
            func = methods[0]
            methods = ()
            return decorator(func)

        # Check for duplicate idents
        dups = [meth_str for meth_str in methods if meth_str in self.methods]
        if dups:
            raise ValueError(
                'Method element(s) for "%s" already exist(s)' %
                '", "'.join(sorted(dups)),
            )

        return decorator

    def mount(self, delegation, *methods, **kwargs):
        """
        Mount another controller class at this path element.  Only one
        delegation is allowed.  The delegation can be restricted to a
        set of HTTP methods by listing the method name strings after
        the controller class; the default is to delegate all HTTP
        methods to the other controller.

        Additional keyword arguments will be passed when creating a
        ``Delegation``, which will subsequently pass them to the
        controller's ``micropath_construct()`` method.

        :param delegation: Another controller to delegate to.  This
                           may be a ``micropath.Controller`` class
                           (not instance), or an instance of a
                           specialized subclass of ``Delegation``; the
                           latter possibility enables mounting other
                           WSGI applications, among other uses.

        :returns: The delegation to be mounted at this path element.
        :rtype: ``Delegation``

        :raises ValueError:
            The delegation has already been set.
        """

        # Make sure the delegation hasn't already been set
        if self.delegation:
            raise ValueError('delegation has already been set')

        # Wrap the delegation, if necessary
        if not isinstance(delegation, Delegation):
            delegation = Delegation(delegation, kwargs)

        # Save ourselves into the delegation so the controller
        # metaclass can do its thing
        delegation.element = self

        # Set the delegation
        if methods:
            # Check for duplicate idents
            dups = [
                meth_str for meth_str in methods if meth_str in self.methods
            ]
            if dups:
                raise ValueError(
                    'Method element(s) for "%s" already exist(s)' %
                    '", "'.join(sorted(dups)),
                )

            # Method restrictions specified, so apply them
            for meth_str in methods:
                if meth_str in self.methods:
                    continue
                meth = Method(meth_str, None, parent=self)
                self.methods[meth.ident] = meth
                meth.delegation = delegation
        else:
            # Delegation on us
            self.delegation = delegation

        return delegation


class Root(Element):
    """
    Represent a root element.  The root element is like a ``Path``
    element, but has no identifier.  A ``micropath.Controller`` class
    has exactly one ``Root`` instance associated with it.
    """

    def __init__(self):
        """
        Initialize a ``Root`` instance.
        """

        # Initialize the superclass
        super(Root, self).__init__(None)

    def set_ident(self, ident):
        """
        Set the element identifier.  This can be used in the case that the
        identifier was not set at construction time.  Subclasses must
        call the superclass abstract method to set the identifier,
        then must update the subordinate lists in the parent object,
        if a parent exists.

        :param str ident: The identifier for the component.  For
                          constant components, this will be the
                          expected value of the component; for
                          variable components, this will be the name
                          of the variable to contain the value.

        :raises ValueError:
            The element identifier has already been set.
        """

        raise ValueError('ident has already been set')

    def add_elem(self, elem, ident=None):
        """
        Add an element to the root.

        :param elem: The element to add.
        :type elem: ``Element``
        :param str ident: The identifier for the component.  Optional.
                          If specified, the first ancestor element
                          without an identifier will have its
                          identifier set to this value.

        :raises ValueError:
            An invalid element is being added.  Could indicate an
            ancestor is missing an identifier (and ``ident`` was not
            set or has been consumed by another element), or an
            element is of an unknown class.
        """

        # Handle the possibility of loops
        seen = set()

        # Walk up the tree
        while True:
            # Loop protection
            assert id(elem) not in seen
            seen.add(id(elem))

            # Sanity-check the element
            if elem is self:
                # Guess it's already been added to us
                return
            elif isinstance(elem, Root):
                raise ValueError('Cannot add a Root element to a Root element')
            elif not isinstance(elem, Method) and not elem.ident:
                # Set the element's ident
                if ident:
                    # It can now be set
                    elem.set_ident(ident)
                    ident = None

            # Have we found the element to be added to the root?
            if not elem.parent:
                break

            # Walk up to the parent
            elem = elem.parent

        # We've found the element to be added to the root, so do so
        if isinstance(elem, Path):
            if elem.ident:
                if elem.ident in self.paths:
                    raise ValueError(
                        'Path element for "%s" already exists' % elem.ident,
                    )
                self.paths[elem.ident] = elem
        elif isinstance(elem, Binding):
            if elem.ident:
                if self.bindings is not None:
                    raise ValueError(
                        'Binding element for "%s" already exists' % elem.ident,
                    )
                self.bindings = elem
        elif isinstance(elem, Method):
            if elem.ident in self.methods:
                raise ValueError(
                    'Method element for "%s" already exists' % elem.ident,
                )
            self.methods[elem.ident] = elem
        else:
            raise ValueError(
                'encountered unknown element class "%s.%s"' %
                (elem.__class__.__module__, elem.__class__.__name__)
            )

        # Set the element's parent
        elem.parent = self


class Path(Element):
    """
    Represent a constant path element.
    """

    def set_ident(self, ident):
        """
        Set the element identifier.  This can be used in the case that the
        identifier was not set at construction time.  Subclasses must
        call the superclass abstract method to set the identifier,
        then must update the subordinate lists in the parent object,
        if a parent exists.

        :param str ident: The identifier for the component.  For
                          constant components, this will be the
                          expected value of the component; for
                          variable components, this will be the name
                          of the variable to contain the value.

        :raises ValueError:
            The element identifier has already been set.
        """

        super(Path, self).set_ident(ident)

        if self.parent:
            if self.ident in self.parent.paths:
                raise ValueError(
                    'Path element for "%s" already exists' % self.ident,
                )
            self.parent.paths[self.ident] = self


class SkipBinding(Exception):
    """
    An exception that may be raised by the validator function of a
    ``Binding``.  This special exception indicates that this binding
    does not match the component and the next component should be
    checked.
    """

    pass


@functools.total_ordering
class Binding(Element):
    """
    Represent a variable path element.  In addition to being in the
    tree, variable path elements have an optional validator function
    (use the ``@Binding.validator`` decorator to set).
    """

    def __init__(self, ident, parent=None):
        """
        Initialize a ``Binding`` instance.

        :param str ident: The identifier for the component.  For
                          variable components, this will be the name
                          of the variable to contain the value.
        :param parent: The parent element.  Defaults to ``None``,
                       indicating the root of the element tree.
        :type parent: ``Element``
        """

        # Call the superclass first
        super(Binding, self).__init__(ident, parent)

        # Initialize the validator and formatter
        self._validator = None
        self._formatter = None

    def __hash__(self):
        """
        Retrieve the hash value of the binding.  This will be the hash
        value of the variable name.

        :returns: The hash value of the binding.
        :rtype: ``int``
        """

        return hash(self.ident)

    def __eq__(self, other):
        """
        Determine if this binding is equal to another binding.  This
        compares the identifiers of the two bindings.

        :param other: The other binding.
        :type other: ``Binding``

        :returns: A ``True`` value if the comparison is true, or
                  ``False`` if not.
        """

        # Can't be equal if other isn't a Binding
        if not isinstance(other, Binding):
            return False

        return self.ident == other.ident

    def __ne__(self, other):
        """
        Determine if this binding is not equal to another binding.  This
        compares the identifiers of the two bindings.

        :param other: The other binding.
        :type other: ``Binding``

        :returns: A ``True`` value if the comparison is true, or
                  ``False`` if not.
        """

        # Can't be equal if other isn't a Binding
        if not isinstance(other, Binding):
            return True

        return self.ident != other.ident

    def __lt__(self, other):
        """
        Determine if this binding is less than another binding.  This
        compares the identifiers of the two bindings.

        :param other: The other binding.
        :type other: ``Binding``

        :returns: A ``True`` value if the comparison is true, or
                  ``False`` if not.  If ``other`` is not a
                  ``Binding``, ``NotImplemented`` is returned.
        """

        # Can't be compared if other isn't a Binding
        if not isinstance(other, Binding):
            return NotImplemented

        return self.ident < other.ident

    def set_ident(self, ident):
        """
        Set the element identifier.  This can be used in the case that the
        identifier was not set at construction time.  Subclasses must
        call the superclass abstract method to set the identifier,
        then must update the subordinate lists in the parent object,
        if a parent exists.

        :param str ident: The identifier for the component.  For
                          constant components, this will be the
                          expected value of the component; for
                          variable components, this will be the name
                          of the variable to contain the value.

        :raises ValueError:
            The element identifier has already been set.
        """

        super(Binding, self).set_ident(ident)

        if self.parent:
            if self.parent.bindings is not None:
                raise ValueError(
                    'Binding element for "%s" already exists' % self.ident,
                )
            self.parent.bindings = self

    def validator(self, func):
        """
        A function decorator that sets the validator function for the
        binding.  If this decorator is not used, no validator function
        is set and the binding always validates.

        The validator function must define a ``value`` parameter,
        which will receive the text value of the path element.
        Dependency injection is used, so the validator function may
        request any other request parameter.  Note that the return
        value of the validator function becomes the value of the
        variable.  Also note that the validator function may raise
        ``SkipBinding`` to cause the next binding to be evaluated; any
        other exception will be bubbled up to the client.

        :param func: The function being decorated.

        :returns: The function that was decorated (``func``).

        :raises ValueError:
            The validator function has already been set.
        """

        # Elements must be immutable
        if self._validator:
            raise ValueError('validator has already been set')

        # Save the validator
        self._validator = func

        # Pre-compute its want signature
        injector.WantSignature.from_func(func)

        # Return the function
        return func

    def validate(self, obj, inj, value):
        """
        Validate a value.  This invokes the validator, if one is set, and
        returns the suitably transformed value to assign to the
        variable.

        :param obj: The instance of the controller class.  This must
                    be passed so that ``self`` can be present in the
                    decorated method.
        :param inj: The dependency injector.
        :type inj: ``micropath.injector.Injector``
        :param value: The value to validate.

        :returns: A suitably transformed value.

        :raises SkipBinding:
            This binding is not applicable to the specified value; try
            any other defined bindings.
        """

        # Call the validator
        if self._validator:
            return inj(self._validator, obj, value=value)

        return value

    def formatter(self, func):
        """
        A function decorator that sets the formatter function for the
        binding.  If this decorator is not used, binding values will
        be converted to URL elements using a simple string conversion
        (``six.text_type`` called on the value).

        Besides ``self``, the formatter function is only passed the
        value; unlike with the ``@validator`` function, dependency
        injection is not available.  The formatter function must
        return a string value.

        :param func: The function being decorated.

        :returns: The function that was decorated (``func``).

        :raises ValueError:
            The formatter function has already been set.
        """

        # Elements must be immutable
        if self._formatter:
            raise ValueError('formatter has already been set')

        # Save the formatter and return the decorated function
        self._formatter = func
        return func

    def format(self, obj, value):
        """
        Format a value.  This converts the value of a binding parameter
        back into a textual URL path component.  If a ``@formatter``
        function has not been set, the value is converted using simple
        string conversion (``six.text_type`` called on the value).

        :param obj: The instance of the controller class.  This must
                    be passed so that ``self`` can be present in the
                    decorated method.
        :param value: The value to validate.

        :returns: A suitably transformed value.
        :rtype: ``str``
        """

        # Call the formatter
        if self._formatter:
            return self._formatter(obj, value)

        return six.text_type(value)


class Method(Element):
    """
    Represent a method route.
    """

    def __init__(self, ident, func, parent=None):
        """
        Initialize a ``Method`` instance.

        :param str ident: The HTTP method.  This will be canonicalized
                          to an uppercase string.  Note that a
                          ``None`` value indicates a fallback for
                          otherwise unspecified methods.
        :param func: The callable that will handle the method.
        :param parent: The parent element.  Defaults to ``None``,
                       indicating the root of the element tree.
        :type parent: ``Element``
        """

        # Canonicalize the ident
        if isinstance(ident, six.string_types):
            ident = ident.upper()

        # Initialize the superclass
        super(Method, self).__init__(ident, parent)

        # Save the function
        self.func = func

    def set_ident(self, ident):
        """
        Set the element identifier.  This can be used in the case that the
        identifier was not set at construction time.  Subclasses must
        call the superclass abstract method to set the identifier,
        then must update the subordinate lists in the parent object,
        if a parent exists.

        :param str ident: The identifier for the component.  For
                          constant components, this will be the
                          expected value of the component; for
                          variable components, this will be the name
                          of the variable to contain the value.

        :raises ValueError:
            The element identifier has already been set.
        """

        raise ValueError('ident has already been set')

    def path(self, ident=None):
        """
        Construct a new subordinate ``Path`` element.

        :param str ident: The identifier for the component.  For
                          constant components, this will be the
                          expected value of the component.  May be
                          ``None`` (the default) to indicate that the
                          metaclass should set the value from the name
                          of the class variable to which the element
                          is assigned.

        :returns: The newly constructed element.
        :rtype: ``Path``
        """

        raise ValueError('cannot attach a path to a method')

    def bind(self, ident=None):
        """
        Construct a new subordinate ``Binding`` element.

        :param str ident: The identifier for the component.  For
                          variable components, this will be the name
                          of the variable to contain the value.  May
                          be ``None`` (the default) to indicate that
                          the metaclass should set the value from the
                          name of the class variable to which the
                          element is assigned.

        :returns: The newly constructed element.
        :rtype: ``Binding``
        """

        raise ValueError('cannot attach a binding to a method')

    def route(self, *methods):
        """
        Method decorator to route HTTP methods to a method.  Called with
        an optional list of method strings (which will be
        canonicalized to uppercase).  If no methods are specified, all
        otherwise undefined methods will be routed to the decorated
        method.  This decorator is designed to work both with and
        without arguments--that is, ``@obj.route`` is equivalent to
        ``@obj.route()``.

        :returns: Either the appropriately decorated method, or a
                  decorator for a method.
        """

        raise ValueError('cannot attach a method to a method')

    def mount(self, delegation, **kwargs):
        """
        Mount another controller class at this path element.  Only one
        delegation is allowed.

        :param delegation: Another controller to delegate to.  This
                           may be a ``micropath.Controller`` class
                           (not instance), or an instance of a
                           specialized subclass of ``Delegation``; the
                           latter possibility enables mounting other
                           WSGI applications, among other uses.

        :returns: The delegation to be mounted at this path element.
        :rtype: ``Delegation``

        :raises ValueError:
            The delegation has already been set.
        """

        # Method is overridden to ensure methods can't be added
        return super(Method, self).mount(delegation, **kwargs)


class Delegation(object):
    """
    Default delegation for controller classes.  Implements the
    descriptor protocol.  Subclasses should override the
    ``micropath_construct()`` method, which is passed the controller
    instance the delegation exists in and should return a new instance
    of the controller class passed to the constructor.
    """

    def __init__(self, controller, kwargs):
        """
        Initialize the ``Delegation`` instance.

        :param controller: A ``micropath.Controller`` class (not
                           instance) that will be delegated to.
        :param dict kwargs: Additional keyword arguments passed when
                            setting up the mount point.
        """

        # Save the controller and keyword arguments
        self.controller = controller
        self.kwargs = kwargs

        # The element may need to be added to the controller's root
        self.element = None

        # Cache of values
        self._cache = {}

    def __get__(self, obj, cls):
        """
        Implement the retriever portion of the descriptor protocol.

        :param obj: An instance of ``cls``.  If the value of the class
                    attribute is requested, this will be ``None``, and
                    this ``Delegation`` instance will be returned.
        :param cls: The class the class attribute is a member of.

        :returns: A properly constructed instance of the controller,
                  or this ``Delegation`` instance if ``obj`` is
                  ``None``.
        """

        # There are times we want to get to the Delegation
        if obj is None:
            return self

        return self.get(obj)

    def __set__(self, obj, value):
        """
        Set the value of the instance attribute.  This is provided for
        testing and debugging purposes.

        :param obj: An instance of the class the class attribute is a
                    member of.
        :param value: The value to assign to the instance attribute.
        """

        self._cache[id(obj)] = value

    def __delete__(self, obj):
        """
        Reset the value of the instance attribute.  This is provided for
        testing and debugging purposes.

        :param obj: An instance of the class the class attribute is a
                    member of.
        """

        # Try hard
        self._cache.pop(id(obj), None)

    def get(self, obj):
        """
        Retrieve a constructed instance of the class being delegated to.
        This calls the ``construct()`` method to construct a new
        instance of the class if necessary.

        :param obj: An instance of the class the class attribute is a
                    member of.

        :returns: An appropriately constructed instance of the target
                  class passed to the constructor.
        """

        key = id(obj)

        # Construct a new one if needed
        if key not in self._cache:
            self._cache[key] = self.construct(obj)

            # Set the parent and element
            self._cache[key]._micropath_parent = obj
            self._cache[key]._micropath_elem = self.element

        return self._cache[key]

    def construct(self, obj):
        """
        Construct a new instance of the controller class passed to the
        constructor.  This default implementation calls the
        ``micropath_construct()`` method, passing it the controller
        class and the keyword arguments set at mount time.

        :param obj: An instance of the class the class attribute is a
                    member of.

        :returns: An appropriately constructed instance of the target
                  class passed to the constructor.
        """

        return obj.micropath_construct(self.controller, self.kwargs)


def path(ident=None):
    """
    Construct a new ``Path`` element.

    :param str ident: The identifier for the component.  For constant
                      components, this will be the expected value of
                      the component.  May be ``None`` (the default) to
                      indicate that the metaclass should set the value
                      from the name of the class variable to which the
                      element is assigned.

    :returns: The newly constructed element.
    :rtype: ``Path``
    """

    return Path(ident)


def bind(ident=None):
    """
    Construct a new ``Binding`` element.

    :param str ident: The identifier for the component.  For variable
                      components, this will be the name of the
                      variable to contain the value.  May be ``None``
                      (the default) to indicate that the metaclass
                      should set the value from the name of the class
                      variable to which the element is assigned.

    :returns: The newly constructed element.
    :rtype: ``Binding``
    """

    # Construct the new binding
    return Binding(ident)


def route(*methods):
    """
    Method decorator to route HTTP methods to a method.  Called with
    an optional list of method strings (which will be canonicalized to
    uppercase).  If no methods are specified, all otherwise undefined
    methods will be routed to the decorated method.  This decorator is
    designed to work both with and without arguments--that is,
    ``@obj.route`` is equivalent to ``@obj.route()``.

    This decorator attaches a list of ``Method`` objects to the
    decorated function; these will be added to the controller class's
    root object appropriately by the metaclass.

    :returns: Either the appropriately decorated method, or a
              decorator for a method.
    """

    def decorator(func):
        meth_list = []

        # Construct the new Method objects
        seen = set()
        if methods:
            for meth_str in methods:
                if meth_str in seen:
                    continue
                seen.add(meth_str)

                meth = Method(meth_str, func)
                meth_list.append(meth)
        else:
            meth = Method(None, func)
            meth_list.append(meth)

        # Attach the method list to the function; this will be picked
        # up by the metaclass
        func._micropath_methods = meth_list

        # Mark the function as a handler
        func._micropath_handler = True

        # Pre-compute its want signature
        injector.WantSignature.from_func(func)

        return func

    # Check if methods consists of a single callable element
    if len(methods) == 1 and callable(methods[0]):
        func = methods[0]
        methods = ()
        return decorator(func)

    return decorator


def mount(delegation, *methods, **kwargs):
    """
    Mount another controller class at this path element.  Only one
    delegation is allowed.  The delegation can be restricted to a set
    of HTTP methods by listing the method name strings after the
    controller class; the default is to delegate all HTTP methods to
    the other controller.

    Additional keyword arguments will be passed when creating a
    ``Delegation``, which will subsequently pass them to the
    controller's ``micropath_construct()`` method.

    :param delegation: Another controller to delegate to.  This may be
                       a ``micropath.Controller`` class (not
                       instance), or an instance of a specialized
                       subclass of ``Delegation``; the latter
                       possibility enables mounting other WSGI
                       applications, among other uses.

    :returns: The delegation to be mounted at the root.
    :rtype: ``Delegation``
    """

    # Wrap the delegation, if necessary
    if not isinstance(delegation, Delegation):
        delegation = Delegation(delegation, kwargs)

    # If methods were specified, create them
    if methods:
        delegation._micropath_methods = []

        seen = set()
        for meth_str in methods:
            if meth_str in seen:
                continue
            seen.add(meth_str)

            meth = Method(meth_str, None)
            delegation._micropath_methods.append(meth)

            # Add the delegation to the Method
            meth.delegation = delegation

    return delegation
