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
