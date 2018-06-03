=======================================
The micropath Web Application Framework
=======================================

.. image:: https://travis-ci.org/klmitch/micropath.svg?branch=master
    :target: https://travis-ci.org/klmitch/micropath

The ``micropath`` web application framework is a framework for
constructing web applications.  It is based on the UNIX philosophy: do
one thing and do it well.  The ``micropath`` framework is ideally
suited for creating microservices, but can easily be used to construct
much larger applications as well.  Users extend the
``micropath.Controller`` class to implement their web application, and
instances of this class can then be used as WSGI applications.  The
``micropath`` framework utilizes a tree structure for routing incoming
requests to the proper handler method, allowing for a significant
speedup over competing systems like ``routes``, which matches an
incoming request against a list of regular expressions.  The
``micropath`` framework also utilizes dependency injection techniques
to pass handler methods only the arguments they need to process the
request.  Finally, requests are represented using the
``micropath.Request`` class, which is a subclass of ``webob.Request``;
handler methods can return ``webob.Response`` objects, or even plain
text (which will be wrapped in a "200 OK" response).

The ``Controller`` Class
========================

The central functionality of ``micropath`` is the ``Controller``
class; creating a WSGI web application using ``micropath`` is as
simple as creating a subclass of ``micropath.Controller`` and
populating it.  The ``micropath.Controller.__call__()`` method
implements a WSGI web application interface, meaning instances of the
``Controller`` subclass are full-fledged WSGI web applications.  There
is also a ``micropath.Controller.__init__()`` method, taking no
arguments, that all subclasses should ensure is called (either by not
overriding it, or by including ``super(ClassName, self).__init__()``
in the implementation).  Aside from these two methods, all other
methods and attributes have names beginning with ``micropath_`` (for
hook and utility methods and data values that developers may override
to customize functionality) or ``_micropath`` (for internal methods
and data values).  This document will touch on some of this
functionality, but for full details, see the help on
``micropath.Controller``.

The most important part of any web application framework is
determining how to route the request to the handler that will act on
that request.  The ``micropath`` framework relies on the special
functions ``micropath.path()`` and ``micropath.bind()``--both of which
return an internal type ``Element`` that includes ``path()`` and
``bind()`` methods as well--to construct the URL path that the web
application is expecting.  Under the covers, this creates a tree-like
object, rooted at the controller, for traversing the URL path of a
request, and should be considerably faster than other frameworks,
which often iterate over a list of regular expressions.  These path
elements are then bound to handler methods using the
``@micropath.route()`` decorator (for requests at the root of the
controller) or ``@Element.route()`` decorator (for requests relative
to an ``Element`` returned by a ``micropath.path()`` or
``micropath.bind()``), which takes as arguments the HTTP methods that
should trigger the handler.  (Note: either form of the ``@route()``
decorator must be the outer-most decorator on a helper method--that
is, the ``@route()`` must be the very first decorator in the source
file.  This decorator stores the function that is passed to it in the
``Element`` tree, so any decorators that occur before it in the source
file will not be invoked when handling a request, even though they
would be if directly accessing the method through the class instance.)

The following example should help clarify how these components work
together.  The example is a part of a REST-style web API for a library
(the dead-tree kind) for handling subscribers::

    class SubscriberController(micropath.Controller):
        @micropath.route('get')
        def index(self):
            # Return a list of subscribers
            ...

        @micropath.route('post')
        def create(self, json_body):
            # Create a new subscriber with details from the JSON body
            ...

        # Bind a subscriber ID to the next path element.  Since no
        # name is passed to ``bind()``, it will default to the
        # variable name "sub_id" (this is done by the metaclass).
        sub_id = micropath.bind()

        @sub_id.route('get')
        def get(self, sub_id):
            # Return the details about a specific subscriber
            ...

        @sub_id.route('put')
        def update(self, sub_id, json_body):
            # Update the subscriber with details from the JSON body
            ...

        @sub_id.route('delete')
        def delete(self, sub_id):
            # Delete the subscriber
            ...

With the above example, an HTTP GET request to "/" would map to the
``index()`` method, while an HTTP PUT request to "/1234" would call
``update()`` with ``sub_id="1234"`` and ``json_body`` being the result
of calling ``json.loads()`` on the request body.  It's also worth
pointing out that ``micropath`` implements a default handler for the
HTTP OPTIONS method; if no handler method has the HTTP OPTIONS method
routed to it, ``micropath`` will return a "204 No Content" response
with the "Allow" header set based on the routed methods.  For
instance, if we sent the HTTP OPTIONS request to "/1234", the "Allow"
header would contain the string "DELETE,GET,HEAD,PUT,OPTIONS".  (The
"HEAD" HTTP method is automatically converted to "GET" by the
``micropath`` routing algorithm and so will be present in "Allow"
anytime "GET" is; and "OPTIONS" is always added, since there's a
default implementation.)

In our toy web API, we might also wish to know what books a given
subscriber has checked out.  There are multiple ways this could be
handled, but for the purposes of the example, we'll assume that we
want a REST resource off the subscriber--e.g., "/1234/books" would
list the books the subscriber has checked out, "/1234/books/5678"
would get details on the checked-out book with id "5678", etc.  With
``micropath``, there are two ways of accomplishing this; the first way
would be to add the following lines to the ``SubscriberController``
class::

    # Bind the "books" path element after the subscriber ID
    books = sub_id.path()

    @books.route('get')
    def books_index(self, sub_id):
        # Return a list of checked-out books
        ...

    @books.route('post')
    def books_create(self, sub_id, json_body):
        # Create (check out) a book under the subscriber from the JSON
        # body
        ...

    # Bind a book ID to the next path element
    book_id = books.bind()

    @book_id.route('get')
    def book_get(self, sub_id, book_id):
        # Return the details about a specific book
        ...

    @book_id.route('put')
    def book_update(self, sub_id, book_id, json_body):
        # Update the book with details from the JSON body
        ...

    @book_id.route('delete')
    def book_delete(self, sub_id, book_id):
        # Delete (check in) the book from the subscriber
        ...

With a simple API, or a microservice-style API, this scheme is
perfectly fine, but for large APIs, the size of the controller class
could become problematic very quickly.  Thus, ``micropath`` provides
another way to accomplish this task: create a ``BookController`` class
providing the functionality for the book resource, then *mount* it on
the ``SubscriberController`` like so::

    # The path() call is given the name "books" by the metaclass; the
    # mount() method configures the path element to delegate requests
    # to that path to the BookController class.  The BookController
    # class will be instantiated when SubscriberController is,
    # assuming that the __init__() method is not overridden, or that
    # the superclass method is called.
    books = sub_id.path().mount(BookController)

Path Binding Validation and Translation
=======================================

In the examples above, the values assigned to ``sub_id`` and
``book_id`` are passed as simple strings to the hook methods.
However, bindings can also have validators and formatters: a
*validator* is a method that is passed the ``value`` argument (and any
other request elements that can be injected, including bindings from
earlier in the path).  The validator should validate that the value is
legal and return whatever object should be passed to handlers.  This
could be used to, for instance, resolve a subscriber ID into an actual
subscriber model object that would subsequently be passed to the
handler methods.  Validators should not raise just any exception,
however; they may raise any of the exceptions contained in
``webob.exc``, which will cause a suitable error to be returned to the
user, or they may raise ``micropath.SkipBinding``, which will
ultimately result in returning a 404 to the client.  Any other
exception will result in a 500 error being returned.

In addition to the validator, a binding may have a *formatter*; this
is a function that will be passed the object that was passed to
``micropath.Request.url_for()`` for that binding, and must return a
string suitable for inclusion in the URL.  An application that uses
the ``url_for()`` method should either provide a formatter or ensure
that the object has an implemented ``__str__()`` method.

Validators and formatters are set by decorating methods with the
``@validator`` and ``@formatter`` decorators, respectively.  For
instance, for the ``SubscriberController`` example above, the
following would set the validator and formatter functions for
``sub_id``::

    @sub_id.validator
    def sub_id_validator(self, value):
        ...

    @sub_id.formatter
    def sub_id_formatter(self, value):
        ...

Requests
========

Handler methods can request the ``Request`` object by listing
``request`` among their arguments.  The ``Request`` class used by
``micropath`` is a subclass of ``webob.Request``, which provides two
additional properties and an additional function.  The ``injector``
property contains a dictionary-like class which is used for
``micropath``'s dependency injection system, and ``base_path``
contains the value of ``script_name`` at the time the request was
constructed by the ``__call__()`` method of ``Controller``.  (The
routing algorithm of ``Controller`` modifies ``script_name`` and
``path_info`` as it routes the request, so a handler method always
sees ``script_name`` as the path to that handler method.)  The
``base_path`` is thus the path to the root ``Controller`` class, and
is used by the ``url_for()`` method.

The ``url_for()`` method allows an application to construct an
absolute URL for any other handler method in the application.  The
first (and only) positional argument that should be passed to
``Request.url_for()`` should be the handler method in question, and
keyword arguments specify the values for bindings.  Note that the
method reference must be to an instance method; passing something like
``SubscriberController.index`` is an error; use something like
``self.index``.  It should also be noted that handler methods can
request a reference to the root controller of the WSGI application by
listing ``root_controller`` among their arguments.  Finally, mounted
controllers can be referenced using the mount point; in the example
above, where a ``BookController`` is mounted on a
``SubscriberController``, the ``index()`` method of the
``BookController`` could be referenced using
``root_controller.books.index``.

Configuration of a ``Controller`` Instance
==========================================

The ``micropath`` framework is not opinionated about the
implementation of the class ``__init__()`` method, other than
requiring, for thread safety purposes, that the superclass's
constructor is called.  This means that applications can provide
configuration information at class construction time.  By default,
mounted classes are passed only keyword arguments provided to the
``mount()`` method (which, typically, must be constants; this
mechanism is intended to allow a controller to tailor its behavior
depending on where it is mounted); however, mounted class construction
can be customized by overriding the ``micropath_construct()`` method
of the controller class onto which another controller is mounted.
This means that configuration information can be propagated to the
other controllers quite easily.

Dependency Injection and Wrapping Decorators
============================================

Handler methods in ``micropath`` are invoked using dependency
injection, passing them the arguments that are declared as part of the
method signature.  However, handler methods are often additionally
decorated with wrapping-type decorators; that is, the decorator
creates a function, typically taking ``*args`` and ``**kwargs``, does
some processing, and then invokes the decorated function (or not,
depending on what the decorator is intended to do).  This affects the
function signature seen by the dependency injector, and could cause
spurious failures.

To counter this problem, the ``micropath`` framework provides a
variation of ``@functools.wraps()``.  The ``@micropath.wraps()``
decorator functions similarly to the ``@functools.wraps()`` decorator,
but has some additional properties.  First, on Python 2.7, it ensures
the ``__wrapped__`` attribute is set (this is implemented by Python
3's ``@functools.wraps()``, but not present in Python 2.7's version);
this makes it easier to get the underlying function, which could be
useful for unit testing.  Second, the ``@micropath.wraps()`` decorator
accepts three additional, optional keyword arguments: ``provides`` can
be a list of keyword arguments that the wrapped function may want that
are provided by the decorator; ``required`` is a list of keyword
arguments that are required by the decorator itself; and ``optional``
is a list of keyword arguments that may be provided if they're
available in the injector.

In addition to the ``@micropath.wraps()`` decorator, the ``micropath``
framework also provides the ``micropath.call_wrapped()`` utility
function.  This function takes as arguments the wrapped function, a
tuple of positional arguments, and a dictionary of keyword arguments,
and invokes the function using the injector machinery, returning the
value of calling the function.  A ``micropath`` decorator may also
wish to know if specific arguments are requested by the function; this
may be determined using ``micropath.wants()``, which takes as
arguments the wrapped function and the name of a keyword argument, and
returns a boolean indicating whether the function wants the specified
keyword argument.

Using the ``@micropath.wraps()`` decorator and the
``micropath.call_wrapped()`` function, function decorators can be
created that wrap a handler method without disrupting the dependency
injection mechanism that is integral to how ``micropath`` calls
handler methods.

Customizing Request Handling
============================

The ``micropath`` framework provides a number of ways of customizing
request handling.  First of all, the class used for representing a
request can be set by overriding the value of
``Controller.micropath_request``; by default, this value is
``micropath.Request``.  (It is highly recommended that custom request
classes extend ``micropath.Request``, so that all functionality is
available.)  Second, the request attributes that are available for
dependency injection are stored in the
``Controller.micropath_request_attrs`` dictionary; additional
attributes can be added by copying
``Controller.micropath_request_attrs`` and adding additional entries
to it.  The keys of this dictionary will be the argument names, and if
the value is ``None`` they will also name the attribute; otherwise,
the value should be the name of the request attribute.

After the request is constructed, the ``micropath`` framework invokes
the ``Controller.micropath_prepare_injector()`` hook method.  The
default implementation does nothing, but this method can be overridden
in the root controller of an application to implement any desired
behavior: authentication headers can be verified, additional data can
be added to the dependency injector, etc.  This is the last step
before traversing the element tree and invoking the proper handler
method.

Several other hook methods exist in the ``micropath.Controller``
class.  For instance, if an error occurs while attempting to evaluate
a request attribute for injection to a handler method, the
``Controller.micropath_request_error()`` hook method is invoked; its
default implementation will return a 400 error to the client.  If, on
the other hand, an exception occurs in a handler method, the
``Controller.micropath_server_error()`` hook method is invoked, which
will, by default, return a 500 error to the client.  If the client's
URL could not be mapped to a controller, the
``Controller.micropath_not_found()`` hook method is called to generate
a 404 error, and ``Controller.micropath_not_implemented()`` is called
if the URL exists, but the specified HTTP method is not routed to a
handler.  Finally, the ``Controller.micropath_options()`` provides the
default implementation for the HTTP OPTIONS method; by default, it
returns a 204 response with the "Allow" header containing a
comma-separated list of recognized HTTP methods.

Methods Requesting ``path_info``
================================

By default, the entire URL must be consumed for a handler method to be
invoked.  However, a handler method may request the ``path_info``
attribute of the request; if the handler method represents the longest
match for the requested URL, the handler will be invoked with the
remaining components of the URL path passed as the ``path_info``
parameter of the handler method.  This effectively inhibits the usual
behavior of returning a 404 response.

Launching a ``micropath`` Application
=====================================

Instances of ``micropath.Controller`` subclasses are fully fledged
WSGI applications.  Many WSGI servers want a module with an
``application`` callable present that is the actual WSGI application;
this attribute may simply be an instance of the root controller.  The
exact semantics depend on the WSGI server, so refer to the
documentation of the server for more details about how to provide the
WSGI application to it.

Instances of ``micropath.Controller`` also have a ``micropath_run()``
utility method.  This method simply uses the Python standard library's
built-in ``wsgiref`` package to launch a simple web server.  By
default, this server will run on the loopback interface ("localhost",
or, more technically, "127.0.0.1") on port 8000, although that can be
controlled using arguments to the method.  Note that this is *NOT
RECOMMENDED* for production systems; this simple server does not
attempt to handle threading, exceptional error handling, SSL, or a
host of other issues that real, production-ready HTTP and WSGI servers
handle.  This is simply meant to simplify testing an application on a
developer's local laptop.

The HEAD HTTP Method
====================

The HTTP specification specifically states that the HEAD method should
act identically to the GET method, except that no body is sent in the
response.  Given that, the ``micropath`` framework treats HEAD as if
it were GET.  In particular, a method that has HEAD routed to it will
never be called unless GET is also routed to that method.
Nevertheless, the ``method`` attribute of the request will contain the
actual HTTP method that was sent.  This also means that the default
OPTIONS response will include HEAD if GET is routed, without any
additional effort on the part of the user.

Controller Inheritance
======================

The element tree built for any given ``micropath.Controller`` subclass
is unique to that specific class.  In particular, this means that a
class that inherits from another class does *not* inherit the URL or
method routing from that class, nor does it inherit the mount points.
However, the hook methods and other customizing data elements are
inherited, as are the actual handler methods and any other methods and
data elements.  Users may take advantage of this by constructing a
base controller class with the needed features, then basing the
application controller classes on that base controller class.
