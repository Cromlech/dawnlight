Dawnlight
=========

.. contents::

About
-----

Dawnlight is an web object publishing system: a system that takes
requests to URLs and translates them to calls to objects. Dawnlight
has a strongly model-based emphasis:

* Dawnlight is *model-based*: both traversal and routing are done
  *first* to models, not to controllers or views directly.

* Dawnlight then looks up a view for the resulting model.

* Dawnlight maintains location information for models: models, whether
  you traverse to them or route to them, know where they are in the
  URL path. With Dawnlight you can always automatically reconstruct
  the URL for a model, no matter whether you obtained it by a query or
  traversed to it using an object graph.

Dawnlight works standalone. It builds on WebOb and integrates as
a WSGI app.

Dawnlight is also designed to work with components in the Zope
Toolkit. It is intended to replace the existing Zope publishing
components with an approach that is easier to understand but at the
same time offers features that the existing Zope publisher does
not. It is intended to replace the publisher in Grok version 2.0.

Dawnlight is primarily inspired by Zope-based frameworks (Grok,
BlueBream) as well as by BFG.


Note on this version
--------------------

This version was made to fit cromlech stack needs, making dawnlight pass from
experimental to useful.

We reduced the scope. Cromlech.dawnlight completes this package with ready
to use components.


Features
--------

* plug into WSGI.

* support for traversal and routing and combinations of the two.

* used by cromlech framework


What is and what isn't in dawnlight
-----------------------------------

Is in Dawnlight
~~~~~~~~~~~~~~~

* object traversal

* custom traversers

* view lookups

* view predicates.


paths and namespaces
--------------------

Dawnlight treats URL path as sequence of steps, where each step is in
a namespace. Let's first consider a URL path::

  /foo/bar/qux

The steps here don't have an explicit namespace, so they will be put
in the default namespace, ``default``.

Namespaces in URLs can also be specified explicitly, with the ``++``
notation::

  /foo/bar/++view++qux

This indicates that ``qux`` is in a special namespace named
``view``. Namespaces are just a name surrounded by ``++``::

  /something/++etc++else

Where ``else`` is in the ``etc`` namespace.

By having namespaces, steps of the same name may exist in multiple
namespaces, and the namespace notation can be used to distinguish
them. This can be useful. Let's imagine we have a collection of some
kind, and users can determine the names of the entries in the
collection. Let's imagine an application where users may create and name
news items and add them to a ``news`` collection::

  /news/stock_goes_up_today

  /news/elephants_invade_the_netherlands

The names ``stock_goes_up_today`` and
``elephants_invade_the_netherlands`` are determined by the user, for
instance by filling it in a form somewhere.

Now let's also imagine we want to have a special way to access the
list of news articles, for instance to get an RSS feed for them. We'll
call this view ``rss``::

  /news/rss

Now we have a problem. What if a user creates a news article with the
name ``rss``? What does the path ``/news/rss`` mean then? Would it
go to the news article or the RSS feed?

With namespaces, we can distinguish the two. If all views are in the
``++view++`` namespace, we can spell accessing the RSS view like this::

  /news/++view++rss

And we can spell accessing the rss article like this::

  /news/rss

Spelling ``++view++`` for a namespace is rather cumbersome. Dawnlight
therefore allows you to consider shortcuts for particular
namespaces. A conventional shortcut for the ``++view++`` namespace is
``@@``. So, ``@@rss`` is equivalent to ``++view++rss``.
 
In many cases, the user does *not* control the spelling of steps. If
news items aren't names but id nnumbers, for instance, we can just
assume that every other name such as ``rss`` can be found in the view
namespace::

  /news/5153

  /news/rss

Shorter urls are nice, so a namespace can be configured to be searched
for even when no explicit namespace marker appears in a URL; the order
in which namespaces are searched can also be configured.


Paths in python
---------------

In Python code, it's useful to consider a path as a list of namespace,
step tuples. So, the path::

  /foo/bar/qux

becomes::

  [(u'default', u'foo'), (u'default', u'bar'), (u'default', u'qux')]

and the path::

  /news/++view++rss

becomes::

  [(u'default', u'news'), (u'view', u'rss')]

Shortcuts like ``@@`` get expanded, so that::

  /news/@@rss

also becomes::

  [(u'default', u'news'), (u'view', u'rss')]

It is often useful to treat a list of steps as a *stack*, which is simply
the reversed list. The stack for ``/foo/bar/qux`` is::

  [(u'default', u'qux'), (u'default', u'bar'), (u'default', u'foo')]


Consuming a path
----------------

Dawnlight decomposes URL path resolution into two separate steps:

* look up the model (content object).

* look up a view on that model.

The model look up starts at a model that is the starting point; the
*root* of the site. The steps in the path are then *consumed*;
consumption can take place one step at the time (traversal) or in
multiple steps at once (routing). Each process of consumption results
in a model, and the steps that could not yet be consumed.

As an example of traversal, we can imagine a structure of nested
dictionaries, where the root dictionary is called ``root``, and a
traversing mechanism that can traverse this structure by doing key
lookup. When we now want to consume the path ``a/b/c``, first ``a``
can be consumed, resulting in the object ``root['a']``. The unconsumed
path left is ``b/c``, so next we can consume ``b`` on the
``root['a']`` object, resulting in ``root['a']['b']``, with the
unconsumed path ``c`` left.  When we consume that last step, we get
``root['a']['b']['c']``, and an empty unconsumed path.

Of course any of these dictionary lookups may fail, in which case the
consumption process is stopped. If for instance ``b`` could not be
found in ``root['a']``, the consumption process is stopped with the
model ``root['a']`` found, and the path ``b/c`` left unconsumed. If
``a`` could not be found, the consumption process stops immediately
with the model ``root`` found and the path ``a/b/c`` left unconsumed.

As an example of routing, we can imagine paths like
``company/4/department/3`` and ``company/1/department/1``. The numbers
in this example are company and department ids; we could for instance
match them with a path pattern like
``company/:company_id/department/:department_id``. The ``company_id``
and ``department_id`` are then looked up in a database, and a
department model is returned matching these ids. The unconsumed path
left is empty in this case.

In Dawnlight, multiple consumption processes may be combined - part of
the path could be consumed by traversal after which routing takes
over, for instance, or vice versa. The end result is always the same:
we end up with a model object and the remaining unconsumed path. The
next step is to look up a view on this model object.


Looking up a view
-----------------

In order to display a model to the web, a view must be looked up for
it. Views can be registered for different classes (or interfaces), and
views are registered by name.

If all steps have been consumed to find the model and therefore no
unconsumed path is left, the view that is looked up is the default
view named ``index``.

If all but one step have been consumed, the last step should indicate
the name of the view.

If there are more than one unconsumed steps then no view can be looked up,
and view lookup fails.

View lookup also fails if no view is registered for the model under
that name.


View layers
-----------

Besides distinguishing views by name and content object, Dawnlight
also supports registration of views for different types of request, to
support a skin mechanism.


Wishes
======

View predicates
---------------

Idea: predicates can be indexed. Known indexes are used to increase
the performance of the view lookup. One index is the interfaces of the
model. Look into geniusql?

Dawnlight also supports view predicates. A Dawnlight view can be
registered with a number of predicates. Only if the predicates match
will the view be returned. Predicates include request method (GET,
PUT, POST), Content-Type, containment, route_name, request_method,
xhr, accept, heade,r path_info (XXX check BFG and expand).

A registration of a view is made using a list of predicates:

 view lookup registry.lookup(iface, name)[('method', 'PUT'),
                                          ('container': Class)]

XXX need to think of clever algorithm which only processes for the registered
predicates for a view, and then can do quick lookup for matches. Needs to
understand inheritance/interfaces in some cases, though.
