# -*- coding: utf-8 -*-

from zope.interface import Interface


class IConsumer(Interface):
    """A consumer is in charge of cannibalizing one or several steps
    in a stack in order to resolve the corresponding object.
    """

    def __call__(stack, obj, request):
        """Returns a boolean meaning that some stack has been consumed,
        an object and the rest of unconsumed stack
        """


class ILookupComponent(Interface):
    """A lookup component is in charge of handling the resolution of a
    specific kind of object. Given the request, the context and a stack,
    it can lookup and return the corresponding object.
    """

    def __call__(request, obj, stack):
        """Returns the right object, given the request,
        the context and the stack.
        """
