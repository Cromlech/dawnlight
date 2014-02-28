# -*- coding: utf-8 -*-

import pytest
import webob
from dawnlight import ResolveError, DEFAULT, VIEW
from dawnlight.stack import parse_path, create_path
from dawnlight.core import ModelLookup, Traverser, ViewLookup
from webtest import TestApp


class Container(dict):
    pass


class Model(object):
    pass


class ModelView(object):

    def __init__(self, request, model):
        self.request = request
        self.model = model

    def __call__(self, environ, start_response):
        response = webob.Response()
        response.unicode_body = u"view of model %r" % self.model
        return response


def view_lookup(request, obj, name):
    return ModelView(request, obj)


def fail_view_lookup(request, obj, name):
    return None


class Application(object):

    def __init__(self, model_lookup, view_lookup, root):
        self.model_lookup = model_lookup
        self.view_lookup = view_lookup
        self.root = root

    def __call__(self, environ, start_response):
        request = webob.Request(environ)
        if request.charset is None:
            request.charset = 'utf8'
        stack = parse_path(request.path)
        model, unconsumed = self.model_lookup(request, self.root, stack)
        view = self.view_lookup(request, model, unconsumed)
        response = view(request, model)
        return response(environ, start_response)


class Traject(object):
    """Consumer that is based on traject.

    Give it a traject.Patterns registry and it will behave according
    to traject.
    """

    def __init__(self, patterns):
        self.patterns = patterns

    def __call__(self, request, obj, stack):
        stack = [name for (ns, name) in stack]
        unconsumed, consumed, obj = self.patterns.consume_stack(
            obj, stack, None)
        unconsumed = [(DEFAULT, name) for name in unconsumed]
        consumed_flag = bool(consumed)
        return consumed_flag, obj, unconsumed


def get_structure():
    """A structure of containers and models.

    The structure is:

    /a
    /sub
    /sub/b

    all starting at root.
    """

    root = Container()
    root.__name__ = u''
    root.__parent___ = None

    a = Model()
    root['a'] = a
    a.__name__ = u'a'
    a.__parent__ = root

    sub = Container()
    root['sub'] = sub
    sub.__name__ = u'sub'
    sub.__parent__ = root

    b = Model()
    sub['b'] = b
    b.__name__ = u'b'
    b.__parent__ = sub

    return root


def test_parse():
    """Parse a path to a stack, default namespaces.
    """
    assert ([(DEFAULT, u'c'),
             (DEFAULT, u'b'),
             (DEFAULT, u'a')] ==
            parse_path(u'/a/b/c'))


def test_multi_slash():
    assert parse_path(u'/a/b/c') == parse_path(u'/a///b//c')
    assert parse_path(u'/a/b/c') == parse_path(u'/a/b/c/')


def test_create():
    assert (u'/a/b/c' ==
            create_path([
                (DEFAULT, u'c'),
                (DEFAULT, u'b'),
                (DEFAULT, u'a')]))


def test_parse_ns():
    """Parse a path to a stack with namespaces.
    """
    assert ([(VIEW, u'c'),
             (DEFAULT, u'b'),
             (DEFAULT, u'a')] ==
            parse_path(u'/a/b/++view++c'))


def test_create_ns():
    assert (u'/a/b/++view++c' ==
            create_path([
                (VIEW, u'c'),
                (DEFAULT, u'b'),
                (DEFAULT, u'a')]))


def test_parse_ns_shortcut():
    assert ([(VIEW, u'c'),
             (DEFAULT, u'b'),
             (DEFAULT, u'a')] ==
            parse_path(u'/a/b/@@c', shortcuts={u'@@': VIEW}))


def test_create_ns_shortcut():
    assert (u'/a/b/@@c' ==
            create_path([
                (VIEW, u'c'),
                (DEFAULT, u'b'),
                (DEFAULT, u'a')], shortcuts={u'@@': VIEW}))


def test_parse_ns_shortcut_not_at_beginning():
    # shortcuts should be at the beginning of a step to be recognized
    assert ([(DEFAULT, u'a@@c'),
             (DEFAULT, u'b'),
             (DEFAULT, u'a')] ==
            parse_path(u'/a/b/a@@c', shortcuts={u'@@': VIEW}))


def test_create_ns_shortcut_not_at_beginning():
    assert (u'/a/b/a@@c' ==
            create_path([
                (DEFAULT, u'a@@c'),
                (DEFAULT, u'b'),
                (DEFAULT, u'a')], shortcuts={u'@@': VIEW}))


def test_parse_ns_weird_no_close():
    # a namespace that opens but doesn't close
    assert (u'/a/b/++c' ==
            create_path([
                (DEFAULT, u'++c'),
                (DEFAULT, u'b'),
                (DEFAULT, u'a')]))


def test_create_ns_weird_no_close():
    assert ([(DEFAULT, u'++c'),
             (DEFAULT, u'b'),
             (DEFAULT, u'a')] ==
            parse_path(u'/a/b/++c'))


def test_parse_ns_weird_no_open():
    # a namespace that closes but doesn't open
    assert ([(DEFAULT, u'view++c'),
             (DEFAULT, u'b'),
             (DEFAULT, u'a')] ==
            parse_path(u'/a/b/view++c'))


def test_create_ns_weird_no_open():
    # a namespace that closes but doesn't open
    assert ([(DEFAULT, u'view++c'),
             (DEFAULT, u'b'),
             (DEFAULT, u'a')] ==
            parse_path(u'/a/b/view++c'))

# XXX removing /./ from paths and checking for ../


def test_resolve_no_consumers():
    lookup = ModelLookup()
    root = get_structure()

    request = webob.Request.blank(u'/a')
    stack = parse_path(request.path)
    obj, unconsumed = lookup(request, root, stack)

    assert obj is root
    assert unconsumed == [(DEFAULT, u'a')]


def test_resolve_traverse():
    lookup = ModelLookup()
    lookup.register(Container, Traverser(traverse_container))

    root = get_structure()

    request = webob.Request.blank(u'/a')
    assert (root['a'], []) == lookup(
        request, root, parse_path(request.path))

    request = webob.Request.blank(u'/sub')
    assert (root['sub'], []) == lookup(
        request, root, parse_path(request.path))

    request = webob.Request.blank(u'/sub/b')
    assert (root['sub']['b'], []) == lookup(
        request, root, parse_path(request.path))

    request = webob.Request.blank(u'/c')
    assert (root, [(DEFAULT, u'c')]) == lookup(
        request, root, parse_path(request.path))

    request = webob.Request.blank(u'/sub/c')
    assert (root[u'sub'], [(DEFAULT, u'c')]) == lookup(
        request, root, parse_path(request.path))


def test_resolve_view():
    lookup = ViewLookup(view_lookup)
    assert isinstance(lookup(webob.Request.blank(u"/"), Model(), ""),
                      ModelView)


def test_view_errors():
    lookup = ViewLookup(fail_view_lookup)

    model = Model()
    request = webob.Request.blank(u"/")

    with pytest.raises(ResolveError) as e:
        lookup(request, model, [(DEFAULT, "a"), (VIEW, "b")])
    assert str(e.value) == (
        "Can't resolve view: stack is not fully consumed.")

    with pytest.raises(ResolveError) as e:
        lookup(request, model, [])
    assert str(e.value) == (
        "Can't resolve view: no default view on %r." % model)

    with pytest.raises(ResolveError) as e:
        lookup(request, model, [(DEFAULT, "test")])
    assert str(e.value) == "'test' is neither a view nor a model."

    with pytest.raises(ResolveError) as e:
        lookup(request, model, [(DEFAULT, "index")])
    assert str(e.value) == "'index' is neither a view nor a model."

    with pytest.raises(ResolveError) as e:
        lookup(request, model, [(VIEW, "index")])
    assert str(e.value) == (
        "Can't resolve view: no view `index` on %r." % model)


def traverse_container(container, ns, name):
    if ns != DEFAULT:
        return None
    return container.get(name)
