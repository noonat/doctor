import functools
import inspect

from doctor._schema import Schema
from doctor._util import UNSET, get_wrapped, make_schema_dict, with_wraps


class Annotation(object):

    """An annotation contains metadata about a Doctor decorated function.

    When the :func:`annotate` decorator is used, it creates an annotation for
    the decorated method and attaches it there. The annotation object contains
    lots of metadata used by Doctor, like the arguments accepted by the
    function and the schema that should be used to validate things.

    :param callable annotated_func:
    :param function func:
    :param list[str] arg_names:
    :param str or None args_name:
    :param str or None kwargs_name:
    :param tuple or None default_values:
    :param Schema schema:
    :param dict args_schema:
    :param dict results_schema:
    """

    _iterable_properties = ('annotated_func', 'func', 'is_method', 'arg_names',
                            'args_name', 'kwargs_name', 'default_values',
                            'schema', 'args_schema', 'result_schema')

    def __init__(self, annotated_func, func, is_method, arg_names, args_name,
                 kwargs_name, default_values, schema, args_schema=None,
                 result_schema=None):
        self.annotated_func = annotated_func
        self.func = func
        self.is_method = is_method
        self.arg_names = arg_names
        self.args_name = args_name
        self.kwargs_name = kwargs_name
        self.default_values = default_values
        self.schema = schema
        self.args_schema = args_schema
        self.result_schema = result_schema

    def __iter__(self):
        for attr in self._iterable_properties:
            yield attr, getattr(self, attr)

    def __eq__(self, other):
        if not isinstance(other, Annotation):
            return False
        for key in self._iterable_properties:
            if getattr(self, key) != getattr(other, key):
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def collect_properties(self, call_args, call_kwargs):
        """Return a dict of properties for validation.

        :param tuple call_args: Positional arguments from the function call.
        :param dict call_kwargs: Keyword arguments from the function call.
        :returns: dict
        """
        properties = {}
        for i, name in enumerate(self.arg_names):
            if name not in self.args_schema['properties']:
                continue
            if i < len(call_args):
                properties[name] = call_args[i]
            elif name in call_kwargs:
                properties[name] = call_kwargs[name]
        return properties

    @classmethod
    def create_args_schema(cls, schema, arg_names, default_values, is_method):
        """Create a schema using the annotated function's arguments.

        :param Schema schema: Source schema.
        :param list[str] arg_names: The names of the function's arguments.
        :param tuple or None default_values: Any default values for the
            function's arguments.
        :param bool is_method: If True, the function will be treated as a
            method and the first argument (self) will be ignored.
        :returns: dict or None
        """
        if is_method:
            # Don't validate the "self" parameter for methods.
            arg_names = arg_names[1:]
        if not arg_names:
            # No parameters, nothing to validate.
            return None

        # Require any positional arguments.
        required_arg_names = arg_names
        if default_values:
            required_arg_names = required_arg_names[:-len(default_values)]
        return make_schema_dict(schema, 'args', arg_names, required_arg_names)

    @classmethod
    def create(cls, _callable, schema, args_schema=UNSET, result_schema=None,
               is_method=False):
        """Create a new Annotation object for the given callable.

        :param callable _callable:
        :param Schema schema:
        :param dict args_schema:
        :param dict result_schema:
        :param bool is_method:
        :returns: Annotation
        """
        if not callable(_callable):
            raise TypeError('{!r} must be a callable (was {!s})'.format(
                _callable, type(_callable)))
        if not isinstance(schema, Schema):
            raise TypeError(('schema should be an instance of Schema '
                             '(was {!r})').format(schema))

        func = _callable
        if not inspect.isfunction(func):
            is_method = True
            func = func.__call__
        func = getattr(func, '__func__', func)

        # Use reflection to get details about the function, so we can use
        # that to generate a schema for it.
        arg_names, args_name, kwargs_name, default_values = (
            inspect.getargspec(func))

        # If they haven't passed an args schema, assume they want to validate
        # all the arguments and create a schema on the fly.
        if args_schema is UNSET:
            args_schema = cls.create_args_schema(schema, arg_names,
                                                 default_values, is_method)

        return Annotation(_callable, func, is_method, arg_names, args_name,
                          kwargs_name, default_values, schema,
                          args_schema=args_schema, result_schema=result_schema)


@with_wraps(arguments=True)
def annotate(schema, args=UNSET, required_args=None, result=None,
             is_method=False):
    """Annotate schema metadata for a method.

    The method's arguments and result will be validated using the schema when
    the method is called, if args or result are specified.

    :param Schema schema: Schema that should be used for validation.
    :param args: If defined, this specifies how to validate the arguments
        to the function.
    :type args: str, dict, list[str], or None
    :param list[str] required_args: If args is a list of strings, these
        arguments will be marked as required.
    :param result: If defined, this specifies how to validate the result of
        the function.
    :type result: str, dict, list[str], or None
    :param bool is_method: If True, treat the annotated function as a method.
        This will ignore the initial argument (self) for validation.
    """
    args_schema = make_schema_dict(schema, 'args', args, required_args)
    result_schema = make_schema_dict(schema, 'result', result)

    def decorator(func):
        annotation = Annotation.create(
            get_wrapped(func), schema, args_schema=args_schema,
            result_schema=result_schema, is_method=is_method)
        func._doctor_annotation = annotation

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if annotation.args_schema is not None:
                properties = annotation.collect_properties(args, kwargs)
                schema.validator.validate(properties, annotation.args_schema)
            result = func(*args, **kwargs)
            if annotation.result_schema is not None:
                schema.validator.validate(result, annotation.result_schema)
            return result
        wrapper._decorated = func
        return wrapper

    return decorator
