=======================================
The micropath Web Application Framework
=======================================

The ``micropath`` web application framework is a framework for
constructing web applications.  It is ideally suited for creating
microservices, but can easily be used to construct much larger
applications as well.  Users extend the ``micropath.Controller`` class
to implement their web application, and instances of this class can
then be used as WSGI applications.  The ``micropath`` framework
utilizes a tree structure for routing incoming requests to the proper
handler method, allowing for a significant speedup over competing
systems like ``routes``, which matches an incoming request against a
list of regular expressions.  The ``micropath`` framework also
utilizes dependency injection techniques to pass handler methods only
the arguments they need to process the request.  Finally, requests are
represented using the ``micropath.Request`` class, which is a subclass
of ``webob.Request``; handler methods can return ``webob.Response``
objects, or even plain text (which will be wrapped in a "200 OK"
response).

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
hook functions and data values that developers may override to
customize functionality) or ``_micropath`` (for internal methods).
This document will touch on some of this functionality, but for full
details, see the help on ``micropath.Controller``.

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
HTTP OPTIONS method; if no handler method has that HTTP method routed
to it, ``micropath`` will return a "204 No Content" response with the
"Allow" header set based on the routed methods.  For instance, if we
sent the HTTP OPTIONS request to "/1234", the "Allow" header would
contain the string "DELETE,GET,HEAD,PUT,OPTIONS".  (The "HEAD" HTTP
method is automatically converted to "GET" by the ``micropath``
routing algorithm and so will be present in "Allow" anytime "GET" is;
and "OPTIONS" is always added, since there's a default
implementation.)
