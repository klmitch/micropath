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
import collections
import functools

import six


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
        self.paths = MergingMap()
        self.bindings = BindingMap()
        self.methods = MergingMap()

        # For delegation to other controllers
        self._delegation = None

        # Allows merging multiple elements into one
        self._master = None

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

    def merge(self, other):
        """
        Merge this element into another element.  This element will
        contain all subordinate elements of the other element, and
        those elements will be updated to have this element as their
        parent.  The other element will be updated to reference this
        element as well.

        :param other: The other element to merge.  Must be a
                      descendant of this element class.
        :type other: ``Element``
        """

        # If we're not the master, delegate to the master
        if self._master:
            self._master.merge(other)
            return

        # Only allow appropriate subclasses
        if not isinstance(other, self.__class__):
            raise ValueError(
                'cannot merge "%s.%s" and "%s.%s"' % (
                    self.__class__.__module__, self.__class__.__name__,
                    other.__class__.__module__, other.__class__.__name__,
                )
            )

        # Validate idents
        if self.ident != other.ident:
            raise ValueError(
                'cannot merge with unequal idents "%s" and "%s"' %
                (self.ident, other.ident)
            )

        # Catch conflicting delegations
        if (self._delegation and other.delegation and
                self._delegation is not other.delegation):
            raise ValueError('cannot merge due to conflicting delegations')

        # Merge parents
        if self.parent and other.parent:
            if self.parent is not other.parent:
                # Merging parents will also merge subordinates
                self.parent.merge(other.parent)
                return
        elif self.parent or other.parent:
            raise ValueError(
                'cannot merge elements at different places in the tree'
            )

        # Walk the other's chain of masters
        while other._master:
            next_master = other._master
            # Repoint the other's master at ours
            other._master = self._master or self
            other = next_master

        # Merge the subordinate lists
        for self_sub, other_sub in [
                (self.paths, other.paths),
                (self.bindings, other.bindings),
                (self.methods, other.methods),
        ]:
            for elem in other_sub.values():
                self_sub[elem.ident] = elem

                # Update the element's parent
                elem.parent = self

        # Make the other element a proxy for this one
        other.paths = self.paths
        other.bindings = self.bindings
        other.methods = self.methods

        # Set the delegation
        if other._delegation:
            self._delegation = other._delegation
        other._delegation = None

        # Finally, set ourself as the master
        other._master = self._master or self

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
            self.paths[elem.ident] = elem

        return elem

    def bind(self, ident=None, before=None, after=None):
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
        elem = Binding(ident, parent=self, before=before, after=after)

        # If it has an identifier, add it to the lists
        if elem.ident:
            self.bindings[elem.ident] = elem

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
                    meth = Method(meth_str, func, parent=self)
                    self.methods[meth.ident] = meth
            else:
                meth = Method(None, func, parent=self)
                self.methods[meth.ident] = meth

            # Mark the function as a handler and save its element
            func._micropath_handler = True
            func._micropath_elem = self

            return func

        # Check if methods consists of a single callable element
        if len(methods) == 1 and callable(methods[0]):
            func = methods[0]
            methods = ()
            return decorator(func)

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

        # Delegate to the master
        if self._master:
            return self._master.mount(delegation, *methods, **kwargs)

        # Make sure the delegation hasn't already been set
        if self._delegation:
            raise ValueError('delegation has already been set')

        # Wrap the delegation, if necessary
        if not isinstance(delegation, Delegation):
            delegation = Delegation(delegation, kwargs)

        # Save ourselves into the delegation so the controller
        # metaclass can do its thing
        delegation.element = self

        # Set the delegation
        if methods:
            # Method restrictions specified, so apply them
            for meth_str in methods:
                meth = Method(meth_str, None, parent=self)
                self.methods[meth.ident] = meth
                meth._delegation = delegation
        else:
            # Delegation on us
            self._delegation = delegation

        return delegation

    @property
    def delegation(self):
        """
        Retrieve the delegation.
        """

        # Defer to the master if necessary
        return self._master.delegation if self._master else self._delegation


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
                # Merge root elements
                self.merge(elem)
                return
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
                self.paths[elem.ident] = elem
        elif isinstance(elem, Binding):
            if elem.ident:
                self.bindings[elem.ident] = elem
        elif isinstance(elem, Method):
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
    (use the ``@Binding.validator`` decorator to set), as well as
    ``before`` and ``after`` sets that may be used to influence the
    order in which variables are tried.
    """

    def __init__(self, ident, parent=None, before=None, after=None):
        """
        Initialize a ``Binding`` instance.

        :param str ident: The identifier for the component.  For
                          variable components, this will be the name
                          of the variable to contain the value.
        :param parent: The parent element.  Defaults to ``None``,
                       indicating the root of the element tree.
        :type parent: ``Element``
        :param before: An iterable of other ``Binding`` instances at
                       the same level of the tree (meaning they have
                       the same parent) which should be checked before
                       trying this binding.
        :param after: An iterable of other ``Binding`` instances at
                      the same level of the tree (meaning they have
                      the same parent) which should be checked after
                      trying this binding.
        """

        # Call the superclass first
        super(Binding, self).__init__(ident, parent)

        # Save the before and after sets
        self.before = set(before or [])
        self.after = set(after or [])

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
            self.parent.bindings[self.ident] = self

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

        # Save the validator and return the decorated function
        self._validator = func
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

    def bind(self, ident=None, before=None, after=None):
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


class MergingMap(collections.MutableMapping):
    """
    Represents a dictionary to which items can be added, but once
    added they cannot be changed or deleted.  This is used to provide
    additional error detection for subordinate path element
    components.
    """

    def __init__(self):
        """
        Initialize an ``MergingMap`` instance.
        """

        # Initialize the map
        self._map = {}

    def __len__(self):
        """
        Retrieve the size of the map.

        :returns: The number of items in the map.
        :rtype: ``int``
        """

        return len(self._map)

    def __iter__(self):
        """
        Iterate over the keys in the map.

        :returns: An iterator of map keys.
        """

        return iter(self._map)

    def __getitem__(self, key):
        """
        Retrieve the item with a given identifier.

        :param str key: The identifier of the element.

        :returns: The specified element.
        :rtype: ``Element``

        :raises KeyError:
            The specified element is not set in the map.
        """

        return self._map[key]

    def __setitem__(self, key, value):
        """
        Set the element with a given identifier.

        :param str key: The identifier of the element.
        :param value: The element.
        :type value: ``Element``
        """

        # Sanity-check the value
        assert key == value.ident

        if key in self._map:
            # Key exists; merge the elements
            self._map[key].merge(value)
        else:
            # Set the value
            self._map[key] = value

    def __delitem__(self, key):
        """
        Delete the element with a given identifier.

        :param str key: The identifier of the element.

        :raises ValueError:
            Keys cannot be deleted once set.

        :raises KeyError:
            The key is not present in the mapping.
        """

        # Don't allow modifications
        if key in self._map:
            raise ValueError('key "%s" cannot be removed from map' % key)

        raise KeyError(key)


# Used as an element in the work queue of BindingMap._visit()
_VisitElem = collections.namedtuple('_VisitElem', ['binding', 'before'])


def _from_adj(adjacency, item):
    """
    Construct a ``_VisitElem`` instance from the adjacency dictionary
    and a specified item from the adjacency dictionary.  This is a
    helper that simplifies the call required to create the queue item.

    :param adjacency: The adjacency dictionary.
    :type adjacency: ``dict`` mapping ``Binding`` to ``set`` of
                     ``Binding``
    :param item: The item to explore.
    :type item: ``Binding``
    """

    return _VisitElem(item, iter(sorted(adjacency.pop(item), reverse=True)))


class BindingMap(MergingMap):
    """
    A mapping of ``Binding`` instances.  This differs from a regular
    dictionary in that the ordering of ``Binding`` instances is
    controlled by the contents of their ``before`` and ``after`` sets
    and the lexicographic ordering of their identifiers.
    """

    def __init__(self):
        """
        Initialize a ``BindingMap`` instance.
        """

        # Initialize the map
        super(BindingMap, self).__init__()

        # Ordering is computed lazily
        self._order = None

    def __iter__(self):
        """
        Iterate over the keys in the binding map.  This topologically
        sorts the bindings based on their ``before`` and ``after``
        sets, using lexicographic sorting to break ties.

        :returns: An iterator of binding identifiers.
        """

        if self._order is None:
            # Start by computing the adjacency map
            adjacency = collections.defaultdict(lambda: set())
            for binding in self._map.values():
                # Collapse before and after into a single before set
                adjacency[binding] |= {other for other in binding.before}
                for other in binding.after:
                    adjacency[other].add(other)

            # Initialize the order list
            self._order = []

            # Kick off the topological sort
            for item in sorted(adjacency, reverse=True):
                # Items may have already been popped, so only visit
                # them if they're still present
                if item in adjacency:
                    self._visit(adjacency, _from_adj(adjacency, item))

            # This algorithm produces a reverse order, so reverse in
            # place
            self._order.reverse()

        # Return an iterator over item identifiers
        return iter(elem.ident for elem in self._order)

    def __setitem__(self, key, value):
        """
        Set the binding with a given identifier.

        :param str key: The identifier of the ``Binding`` instance.
        :param value: The actual binding.
        :type value: ``Binding``

        :raises ValueError:
            The key has already been set.
        """

        super(BindingMap, self).__setitem__(key, value)

        # Invalidate the order cache
        self._order = None

    def _visit(self, adjacency, elem):
        """
        Implement the inner visit of the topological sort algorithm.

        :param adjacency: The adjacency dictionary, as computed by
                          ``__iter__()`` and updated by previous
                          ``_visit()`` invocations.
        :type adjacency: ``dict`` mapping ``Binding`` to ``set`` of
                         ``Binding``
        """

        # Work queue
        queue = [elem]

        while queue:
            try:
                # Get the next binding that should be before this one
                binding = six.next(queue[-1].before)
                if binding in adjacency:
                    # Pop that node off the adjacency map and add it
                    # to the queue
                    queue.append(_from_adj(adjacency, binding))
            except StopIteration:
                # Explored all its dependencies, add it to the results
                self._order.append(queue.pop().binding)


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


def bind(ident=None, before=None, after=None):
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
    return Binding(ident, before=before, after=after)


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
        if methods:
            for meth_str in methods:
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

        for meth_str in methods:
            meth = Method(meth_str, None)
            delegation._micropath_methods.append(meth)

            # Add the delegation to the Method
            meth._delegation = delegation

    return delegation
