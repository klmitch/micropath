=======================================
The micropath Web Application Framework
=======================================

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
should trigger the handler.

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
