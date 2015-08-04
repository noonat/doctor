# import functools

import mock
import pytest
from jsonschema.exceptions import ValidationError

from doctor import Annotation, annotate, get_wrapped
from doctor._schema import Schema


@pytest.fixture(scope='module')
def schema():
    return Schema({
        'definitions': {
            'a': {'type': 'string'},
            'b': {'type': 'boolean'},
            'c': {'type': 'integer'},
            'd': {'type': 'integer'},
            'result': {
                'type': 'integer',
                'maximum': 2
            }
        }
    })


def test_annotation(schema):
    s = mock.sentinel

    a = Annotation(s.annotated_func, s.func, s.is_method, s.arg_names,
                   s.args_name, s.kwargs_name, s.default_values, s.schema,
                   s.args_schema, s.result_schema)
    assert a.annotated_func == s.annotated_func
    assert a.func == s.func
    assert a.is_method == s.is_method
    assert a.arg_names == s.arg_names
    assert a.args_name == s.args_name
    assert a.kwargs_name == s.kwargs_name
    assert a.default_values == s.default_values
    assert a.schema == s.schema
    assert a.args_schema == s.args_schema
    assert a.result_schema == s.result_schema

    a2 = Annotation(s.annotated_func, s.func, s.is_method, s.arg_names,
                    s.args_name, s.kwargs_name, s.default_values, s.schema,
                    s.args_schema, s.result_schema)
    assert a == a2
    a2.annotated_func = s.other_annotated_func
    assert a != a2
    assert a != object()

    a = Annotation(s.annotated_func, s.func, s.is_method, s.arg_names,
                   s.args_name, s.kwargs_name, s.default_values, s.schema)
    assert a.args_schema is None
    assert a.result_schema is None


def test_annotation_collect_properties(schema):
    @annotate(schema)
    def func(a, b, c=3, d=4):
        pass

    annotation = get_wrapped(func)._doctor_annotation
    collect_properties = annotation.collect_properties
    properties = collect_properties((1, 2), {})
    assert properties == {'a': 1, 'b': 2}
    properties = collect_properties((1, 2, 3, 4), {})
    assert properties == {'a': 1, 'b': 2, 'c': 3, 'd': 4}
    properties = collect_properties((1, 2), {'c': 3, 'd': 4})
    assert properties == {'a': 1, 'b': 2, 'c': 3, 'd': 4}
    properties = collect_properties((1, 2), {'d': 3})
    assert properties == {'a': 1, 'b': 2, 'd': 3}


def test_annotation_collect_properties_method(schema):
    """It should strip self for things marked as a method."""

    s = mock.sentinel

    @annotate(schema, is_method=True)
    def method(self, a, b, c=3, d=4):
        pass

    annotation = get_wrapped(method)._doctor_annotation
    collect_properties = annotation.collect_properties
    properties = collect_properties((s.self, 1, 2), {})
    assert properties == {'a': 1, 'b': 2}
    properties = collect_properties((s.self, 1, 2, 3, 4), {})
    assert properties == {'a': 1, 'b': 2, 'c': 3, 'd': 4}
    properties = collect_properties((s.self, 1, 2), {'c': 3, 'd': 4})
    assert properties == {'a': 1, 'b': 2, 'c': 3, 'd': 4}
    properties = collect_properties((s.self, 1, 2), {'d': 3})
    assert properties == {'a': 1, 'b': 2, 'd': 3}


def test_annotate(schema):
    @annotate(schema)
    def func():
        pass

    wrapped_func = get_wrapped(func)
    assert dict(wrapped_func._doctor_annotation) == {
        'annotated_func': wrapped_func,
        'func': wrapped_func,
        'is_method': False,
        'arg_names': [],
        'args_name': None,
        'kwargs_name': None,
        'default_values': None,
        'schema': schema,
        'args_schema': None,
        'result_schema': None
    }


def test_annotate_args_none(schema):
    """It should allow you to specify None to disable argument validation."""

    @annotate(schema, args=None)
    def func(a, b):
        pass

    wrapped_func = get_wrapped(func)
    assert dict(wrapped_func._doctor_annotation) == {
        'annotated_func': wrapped_func,
        'func': wrapped_func,
        'is_method': False,
        'arg_names': ['a', 'b'],
        'args_name': None,
        'kwargs_name': None,
        'default_values': None,
        'schema': schema,
        'args_schema': None,
        'result_schema': None
    }


def test_annotate_args_list(schema):
    """It should allow you to pass a list of args to validate.

    This should override the list of arguments in the function.
    """

    @annotate(schema, args=['a', 'b'])
    def func(foo, bar='baz'):
        pass

    wrapped_func = get_wrapped(func)
    assert dict(wrapped_func._doctor_annotation) == {
        'annotated_func': wrapped_func,
        'func': wrapped_func,
        'is_method': False,
        'arg_names': ['foo', 'bar'],
        'args_name': None,
        'kwargs_name': None,
        'default_values': ('baz',),
        'schema': schema,
        'args_schema': {
            'type': 'object',
            'additionalProperties': True,
            'properties': {
                'a': {'$ref': '#/definitions/a'},
                'b': {'$ref': '#/definitions/b'}
            }
        },
        'result_schema': None
    }


def test_annotate_args_list_required(schema):
    """It should allow you to pass a list of required args."""

    @annotate(schema, args=['a', 'b', 'c'], required_args=['a', 'b'])
    def func(foo, bar='baz'):
        pass

    wrapped_func = get_wrapped(func)
    assert dict(wrapped_func._doctor_annotation) == {
        'annotated_func': wrapped_func,
        'func': wrapped_func,
        'is_method': False,
        'arg_names': ['foo', 'bar'],
        'args_name': None,
        'kwargs_name': None,
        'default_values': ('baz',),
        'schema': schema,
        'args_schema': {
            'type': 'object',
            'additionalProperties': True,
            'properties': {
                'a': {'$ref': '#/definitions/a'},
                'b': {'$ref': '#/definitions/b'},
                'c': {'$ref': '#/definitions/c'}
            },
            'required': ['a', 'b']
        },
        'result_schema': None
    }


def test_annotate_args_dict(schema):
    """It should allow you to pass in an explicit schema as a dictionary."""


def test_annotate_func_with_args(schema):
    """It should treat positional arguments as required."""

    @annotate(schema)
    def func_with_args(a, b):
        pass

    wrapped_func = get_wrapped(func_with_args)
    assert dict(wrapped_func._doctor_annotation) == {
        'annotated_func': wrapped_func,
        'func': wrapped_func,
        'is_method': False,
        'arg_names': ['a', 'b'],
        'args_name': None,
        'kwargs_name': None,
        'default_values': None,
        'schema': schema,
        'args_schema': {
            'type': 'object',
            'additionalProperties': True,
            'properties': {
                'a': {'$ref': '#/definitions/a'},
                'b': {'$ref': '#/definitions/b'}
            },
            'required': ['a', 'b']
        },
        'result_schema': None
    }


def test_annotate_func_with_default_args(schema):
    """It should treat arguments with default values as optional."""

    s = mock.sentinel

    @annotate(schema)
    def func_with_default_args(a, b, c=s.default_c, d=s.default_d):
        pass

    wrapped_func = get_wrapped(func_with_default_args)
    assert dict(wrapped_func._doctor_annotation) == {
        'annotated_func': wrapped_func,
        'func': wrapped_func,
        'is_method': False,
        'arg_names': ['a', 'b', 'c', 'd'],
        'args_name': None,
        'kwargs_name': None,
        'default_values': (s.default_c, s.default_d),
        'schema': schema,
        'args_schema': {
            'type': 'object',
            'additionalProperties': True,
            'properties': {
                'a': {'$ref': '#/definitions/a'},
                'b': {'$ref': '#/definitions/b'},
                'c': {'$ref': '#/definitions/c'},
                'd': {'$ref': '#/definitions/d'}
            },
            'required': ['a', 'b']
        },
        'result_schema': None
    }


def test_annotate_func_with_all_default_args(schema):
    """It should correctly handle a function with all optional arguments."""

    s = mock.sentinel

    @annotate(schema)
    def func_with_default_args(a=s.default_a, b=s.default_b):
        pass

    wrapped_func = get_wrapped(func_with_default_args)
    assert dict(wrapped_func._doctor_annotation) == {
        'annotated_func': wrapped_func,
        'func': wrapped_func,
        'is_method': False,
        'arg_names': ['a', 'b'],
        'args_name': None,
        'kwargs_name': None,
        'default_values': (s.default_a, s.default_b),
        'schema': schema,
        'args_schema': {
            'type': 'object',
            'additionalProperties': True,
            'properties': {
                'a': {'$ref': '#/definitions/a'},
                'b': {'$ref': '#/definitions/b'},
            }
        },
        'result_schema': None
    }


def test_annotate_with_result(schema):
    """It should allow you to specify a result schema."""

    s = mock.sentinel

    @annotate(schema, result='c')
    def func_with_result(a, b=s.default_b):
        pass

    wrapped_func = get_wrapped(func_with_result)
    assert dict(func_with_result._doctor_annotation) == {
        'annotated_func': wrapped_func,
        'func': wrapped_func,
        'is_method': False,
        'arg_names': ['a', 'b'],
        'args_name': None,
        'kwargs_name': None,
        'default_values': (s.default_b,),
        'schema': schema,
        'args_schema': {
            'type': 'object',
            'additionalProperties': True,
            'properties': {
                'a': {'$ref': '#/definitions/a'},
                'b': {'$ref': '#/definitions/b'},
            },
            'required': ['a']
        },
        'result_schema': {
            '$ref': '#/definitions/c'
        }
    }


def test_annotate_is_method(schema):
    """If is_method=True, the first argument ("self") should be ignored."""

    s = mock.sentinel

    class SomeClass(object):
        @annotate(schema, is_method=True)
        def method(self, a, b, c=s.default_c, d=s.default_d):
            pass

    wrapped_method = get_wrapped(SomeClass.method)
    assert dict(wrapped_method._doctor_annotation) == {
        'annotated_func': wrapped_method,
        'func': wrapped_method,
        'is_method': True,
        'arg_names': ['self', 'a', 'b', 'c', 'd'],
        'args_name': None,
        'kwargs_name': None,
        'default_values': (s.default_c, s.default_d),
        'schema': schema,
        'args_schema': {
            'type': 'object',
            'additionalProperties': True,
            'properties': {
                'a': {'$ref': '#/definitions/a'},
                'b': {'$ref': '#/definitions/b'},
                'c': {'$ref': '#/definitions/c'},
                'd': {'$ref': '#/definitions/d'}
            },
            'required': ['a', 'b']
        },
        'result_schema': None
    }


def test_annotate_with_callable(schema):
    s = mock.sentinel

    class SomeCallable(object):
        __name__ = 'SomeCallable'

        def __init__(self):
            pass

        def __call__(self, a, b, c=s.default_c, d=s.default_d):
            pass

    some_callable = annotate(schema)(SomeCallable())
    wrapped_method = get_wrapped(some_callable)
    assert dict(wrapped_method._doctor_annotation) == {
        'annotated_func': wrapped_method,
        'func': getattr(SomeCallable.__call__, '__func__',
                        SomeCallable.__call__),
        'is_method': True,
        'arg_names': ['self', 'a', 'b', 'c', 'd'],
        'args_name': None,
        'kwargs_name': None,
        'default_values': (s.default_c, s.default_d),
        'schema': schema,
        'args_schema': {
            'type': 'object',
            'additionalProperties': True,
            'properties': {
                'a': {'$ref': '#/definitions/a'},
                'b': {'$ref': '#/definitions/b'},
                'c': {'$ref': '#/definitions/c'},
                'd': {'$ref': '#/definitions/d'}
            },
            'required': ['a', 'b']
        },
        'result_schema': None
    }


def test_annotate_validation(schema):
    calls = []

    @annotate(schema, result='result')
    def func(a, b, c=0, d=0):
        calls.append(mock.call(a, b, c=c, d=d))
        return d

    assert func('foo', True) == 0
    assert func('foo', True, c=1, d=2) == 2
    assert calls == [mock.call('foo', True, c=0, d=0),
                     mock.call('foo', True, c=1, d=2)]
    with pytest.raises(ValidationError):
        # It should raise if the params fail validation.
        func('foo', 'bad')
    with pytest.raises(ValidationError):
        # It should raise if the result fails validation.
        func('foo', True, d=100)
