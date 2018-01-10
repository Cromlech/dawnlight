# -*- coding: utf-8 -*-

from dawnlight import DEFAULT, VIEW
from dawnlight.interfaces import IConsumer, ILookupComponent
from zope.interface.adapter import AdapterRegistry
from zope.interface import implementer, implementedBy, providedBy
from zope.interface.interfaces import ISpecification


class ResolveError(Exception):
    """Exception raised when a path resolution fails.
    """


@implementer(ILookupComponent)
class ModelLookup(object):
    """Looks up a model using consumers.
    """

    def __init__(self):
        self._reg = AdapterRegistry()

    def register(self, class_or_interface, consumer):
        """Registers a new consumer.
        """
        source = (_get_interface(class_or_interface),)
        self._reg.subscribe(source, IConsumer, consumer)

    def lookup(self, obj):
        """Get all consumers.
        """
        provided = (providedBy(obj),)
        return self._reg.subscriptions(provided, IConsumer)

    def __call__(self, request, obj, stack):
        """Traverses following stack components and starting from obj.
        """
        unconsumed = stack.copy()
        while unconsumed:
            for consumer in self.lookup(obj):
                any_consumed, obj, unconsumed = consumer(
                    request, obj, unconsumed)
                if any_consumed:
                    break
            else:
                # nothing could be consumed
                return obj, unconsumed
        return obj, unconsumed


@implementer(ILookupComponent)
class ViewLookup(object):
    """Looks up a view using a given method.
    """
    default_name = u'index'

    def __init__(self, lookup):
        """`lookup` is a function which received request,
        object and a name and shall provide a view.
        """
        self.lookup = lookup

    def __call__(self, request, obj, stack):
        """Resolves a view.
        """
        default_fallback = False
        unconsumed_amount = len(stack)
        if unconsumed_amount == 0:
            default_fallback = True
            ns, name = VIEW, self.default_name
        elif unconsumed_amount == 1:
            ns, name = stack[0]
        else:
            raise ResolveError(
                "Can't resolve view: stack is not fully consumed.")

        if ns not in (DEFAULT, VIEW):
            raise ResolveError(
                "Can't resolve view: namespace %r is not supported." % ns)

        view = self.lookup(request, obj, name)
        if view is None:
            if default_fallback:
                raise ResolveError(
                    "Can't resolve view: no default view on %r." % obj)
            else:
                if ns == VIEW:
                    raise ResolveError(
                        "Can't resolve view: no view `%s` on %r." % (name, obj))
                raise ResolveError(
                    "%r is neither a view nor a model." % name)
        return view


def _get_interface(class_or_interface):
    if ISpecification.providedBy(class_or_interface):
        return class_or_interface
    return implementedBy(class_or_interface)


@implementer(ILookupComponent)
class Traverser(object):
    """A traverser is a consumer that consumes only a single step.

    Only the top of the stack is popped.

    Should be constructed with a traversal function. The function
    takes three arguments: the object to traverse into, and the namespace
    and name to traverse. It should return either the object traversed towards,
    or None if this object cannot be found.
    """

    def __init__(self, func):
        self.func = func

    def __call__(self, request, obj, stack):
        ns, name = stack.popleft()
        next_obj = self.func(obj, ns, name)
        if next_obj is None:
            stack.append((ns, name))
            return False, obj, stack
        return True, next_obj, stack
