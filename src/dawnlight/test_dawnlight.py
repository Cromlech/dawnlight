# -*- coding: utf-8 -*-

import pytest
import webob
from dawnlight import ResolveError, DEFAULT, VIEW
from dawnlight.stack import parse_path, create_path
from dawnlight.core import ModelLookup, Traverser, ViewLookup


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


def get_structure():
    """A structure of containers and models.

    The structure is:

    /a
    /sub
    /sub/b

    all starting at root.
    """

    root = Container()
    root.__name__ = ''
    root.__parent___ = None

    a = Model()
    root['a'] = a
    a.__name__ = 'a'
    a.__parent__ = root

    sub = Container()
    root['sub'] = sub
    sub.__name__ = 'sub'
    sub.__parent__ = root

    b = Model()
    sub['b'] = b
    b.__name__ = 'b'
    b.__parent__ = sub

    return root


def test_parse():
    """Parse a path to a stack, default namespaces.
    """
    assert ([(DEFAULT, 'a'),
             (DEFAULT, 'b'),
             (DEFAULT, 'c')] ==
            list(parse_path('/a/b/c')))


def test_multi_slash():
    assert parse_path('/a/b/c') == parse_path('/a///b//c')
    assert parse_path('/a/b/c') == parse_path('/a/b/c/')


def test_create():
    assert ('/a/b/c' ==
            create_path([
                (DEFAULT, 'a'),
                (DEFAULT, 'b'),
                (DEFAULT, 'c')]))


def test_parse_ns():
    """Parse a path to a stack with namespaces.
    """
    assert ([(DEFAULT, 'a'),
             (DEFAULT, 'b'),
             (VIEW, 'c')] ==
            list(parse_path('/a/b/++view++c')))


def test_create_ns():
    assert ('/a/b/++view++c' ==
            create_path([
                (DEFAULT, 'a'),
                (DEFAULT, 'b'),
                (VIEW, 'c')]))


def test_parse_ns_shortcut():
    assert ([(DEFAULT, 'a'),
             (DEFAULT, 'b'),
             (VIEW, 'c')] ==
            list(parse_path('/a/b/@@c', shortcuts={'@@': VIEW})))


def test_create_ns_shortcut():
    assert ('/a/b/@@c' ==
            create_path([
                (DEFAULT, 'a'),
                (DEFAULT, 'b'),
                (VIEW, 'c')], shortcuts={'@@': VIEW}))


def test_parse_ns_shortcut_not_at_beginning():
    # shortcuts should be at the beginning of a step to be recognized
    assert ([(DEFAULT, 'a'),
             (DEFAULT, 'b'),
             (DEFAULT, 'a@@c')] ==
            list(parse_path('/a/b/a@@c', shortcuts={'@@': VIEW})))


def test_create_ns_shortcut_not_at_beginning():
    assert ('/a/b/a@@c' ==
            create_path([
                (DEFAULT, 'a'),
                (DEFAULT, 'b'),
                (DEFAULT, 'a@@c')], shortcuts={'@@': VIEW}))


def test_create_ns_weird_no_close():
    # a namespace that opens but doesn't close
    assert ('/a/b/++c' ==
            create_path([
                (DEFAULT, 'a'),
                (DEFAULT, 'b'),
                (DEFAULT, '++c')]))


def test_parse_ns_weird_no_close():
    assert ([(DEFAULT, 'a'),
             (DEFAULT, 'b'),
             (DEFAULT, '++c')] ==
            list(parse_path('/a/b/++c')))


def test_parse_ns_weird_no_open():
    # a namespace that closes but doesn't open
    assert ([(DEFAULT, 'a'),
             (DEFAULT, 'b'),
             (DEFAULT, 'view++c')] ==
            list(parse_path('/a/b/view++c')))


def test_create_ns_weird_no_open():
    # a namespace that closes but doesn't open
    assert ('/a/b/view++c' ==
            create_path([
                (DEFAULT, 'a'),
                (DEFAULT, 'b'),
                (DEFAULT, 'view++c')]))

# XXX removing /./ from paths and checking for ../


def test_resolve_no_consumers():
    lookup = ModelLookup()
    root = get_structure()

    request = webob.Request.blank('/a')
    stack = parse_path(request.path)
    obj, unconsumed = lookup(request, root, stack)

    assert obj is root
    assert list(unconsumed) == [(DEFAULT, 'a')]


def test_resolve_traverse():
    lookup = ModelLookup()
    lookup.register(Container, Traverser(traverse_container))

    root = get_structure()

    request = webob.Request.blank('/a')
    obj, left = lookup(request, root, parse_path(request.path))
    assert obj == root['a'] and not left

    request = webob.Request.blank('/sub')
    obj, left = lookup(request, root, parse_path(request.path))
    assert obj == root['sub'] and not left

    request = webob.Request.blank('/sub/b')
    obj, left = lookup(request, root, parse_path(request.path))
    assert obj == root['sub']['b'] and not left

    request = webob.Request.blank('/c')
    obj, left = lookup(request, root, parse_path(request.path))
    assert obj == root and list(left) == [(DEFAULT, 'c')]

    request = webob.Request.blank('/sub/c')
    obj, left = lookup(request, root, parse_path(request.path))
    assert obj == root['sub'] and list(left) == [(DEFAULT, 'c')]

    # We make sure the stack is untouched by the traversing
    request = webob.Request.blank('/sub/c')
    stack = parse_path(request.path)
    obj, left = lookup(request, root, parse_path(request.path))
    assert list(left) == [(DEFAULT, 'c')]
    assert list(stack) == [('default', 'sub'), ('default', 'c')]


def test_resolve_view():
    lookup = ViewLookup(view_lookup)
    view = lookup(webob.Request.blank(u"/"), Model(), stack=[])
    assert isinstance(view, ModelView)


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
