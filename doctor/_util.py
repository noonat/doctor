import functools

import six


class Unset(object):

    def __repr__(self):
        return '<unset>'


#: Default argument for functions where None can't be used.
UNSET = Unset()


def get_wrapped(func):
    """Find the wrapped function in a chain of decorators.

    This looks for a _wraps attribute on the function, and returns the first
    one in the chain that doesn't have that attribute. Note that this requires
    decorators to set a _wraps attribute on the wrapper functions they return.
    See :func:`~with_wraps` for an easy to to augment existing decorators with
    this functionality.

    :param callable func: A function, probably created by a decorator.
    :returns: callable
    """
    while hasattr(func, '_wraps'):
        func = func._wraps
    return func


def make_schema_dict(schema, usage, names, required_names=None):
    """Create a new schema in various ways, depending on the parameters.

    :param Schema schema: The source schema. References attributes must be
        defined in this schema.
    :param str usage: What this schema will be used for (e.g. "args").
    :param names: If a string, this will be treated as a fragment and resolved
        in the given schema to find the required schema. If a list, it will
        be treated as a list of names and combined with required_names to
        generate a schema on the fly. If a dict, it will used directly.
    :type names: str, dict, list[str], or None
    :param list[str] required_names: If names is a list of strings, this will
        be used to enumerate which of those named properties are required.
    :returns: dict
    :raises TypeError: if the names argument is not a valid type.
    :raises jsonschema.exceptions.RefResolutionError: if one of the names
        can't be found in the schema's definitions block.
    """
    if names is UNSET:
        return UNSET
    elif names is None:
        new_schema = None
    elif isinstance(names, six.string_types):
        ref = '#/definitions/{}'.format(names)
        schema.resolve(ref)
        new_schema = {'$ref': ref}
    elif isinstance(names, dict):
        new_schema = names
    elif isinstance(names, list):
        new_schema = {'type': 'object',
                      'additionalProperties': True,
                      'properties': {}}
        for name in names:
            # Validate that the referenced name actually exists in the schema's
            # definitions block. This will raise RefResolutionError if the
            # definition is missing.
            ref = '#/definitions/{}'.format(name)
            schema.resolve(ref)
            new_schema['properties'][name] = {'$ref': ref}
        if required_names:
            new_schema['required'] = required_names
    else:
        raise TypeError(('{usage!r} must be a str, dict, list[str], or '
                         'None').format(usage=usage))
    return new_schema


def with_wraps(decorator=None, arguments=False):
    """Wrap another decorator and set _wraps on decorated functions.

    This is used to programatically find the root of a chain of decorators.
    Doctor needs to know this so it can introspect the *real* function and
    figure out its arguments. :func:`~with_wraps` is used to modify existing
    decorators to ensure they set the _wraps attribute that Doctor looks for
    on decorated functions.

    :param callable decorator: Decorator to wrap.
    :param bool arguments: If True, will expect to wrap a decorator which in
        turn takes arguments and returns another decorator.
    """
    if decorator is None and arguments:
        # Called as with_wraps(arguments=True), which means we need to return
        # a version of with_wraps which will call itself with arguments=True
        # to decorate another function (which in turn accepts arguments and
        # returns a decorator).
        @functools.wraps(with_wraps)
        def _with_wraps_decorator(decorator):
            return with_wraps(decorator, arguments=True)
        return _with_wraps_decorator
    elif decorator is None:
        # Someone called this as with_wraps(), probably on accident.
        raise TypeError('decorator is None, must be a callable. Please use '
                        '@with_wraps or @with_wraps(arguments=True).')

    @functools.wraps(decorator)
    def _decorator_wrapper(*args, **kwargs):
        if arguments:
            generated_decorator = decorator(*args, **kwargs)
            return with_wraps(generated_decorator)
        else:
            if not args:
                raise TypeError(
                    'Decorator for {!r} called without arguments. This '
                    'usually means you wrote @with_wraps but should have '
                    'written @with_wraps(arguments=True).'.format(decorator))
            func = args[0]
            if not callable(func):
                raise TypeError('first argument to decorator must be callable')
            wrapped_func = decorator(func)
            wrapped_func._wraps = func
            return wrapped_func
    return _decorator_wrapper
