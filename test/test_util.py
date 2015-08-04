import functools

import jsonschema
import mock
import pytest

from doctor import get_wrapped, with_wraps
from doctor._schema import Schema
from doctor._util import make_schema_dict


def test_get_wrapped():
    s = mock.sentinel

    @with_wraps
    def foo(func):
        @functools.wraps(func)
        def wrapper(results):
            results.append(s.foo)
            return func(results)
        return wrapper

    @with_wraps(arguments=True)
    def bar():
        def decorator(func):
            @functools.wraps(func)
            def wrapper(results):
                results.append(s.bar)
                return func(results)
            return wrapper
        return decorator

    @foo
    @bar()
    @foo
    @bar()
    def baz(results):
        results.append(s.baz)
        return results

    assert baz([]) == [s.foo, s.bar, s.foo, s.bar, s.baz]
    wrapped = get_wrapped(baz)
    assert wrapped([]) == [s.baz]

    def qux():
        pass

    assert get_wrapped(qux) == qux


def test_make_schema_dict():
    raw_schema = {
        'definitions': {
            'id': {'type': 'integer'},
            'email': {'type': 'string'},
            'user': {
                'type': 'object',
                'properties': {
                    'id': {'$ref': '#/definitions/id'},
                    'email': {'$ref': '#/definitions/email'}
                },
            }
        }
    }
    schema = Schema(raw_schema)

    # Passing nothing should return nothing (meaning no validation). This is
    # supported because the default value is None on annotate().
    assert make_schema_dict(schema, 'args', None) is None

    # Passing a definition name should return the definition
    assert (make_schema_dict(schema, 'args', 'user') ==
            {'$ref': '#/definitions/user'})

    # Passing a custom schema dictionary should return that dictionary
    custom_schema = {'type': 'boolean'}
    assert make_schema_dict(schema, 'args', custom_schema) == custom_schema

    # Passing a list of names should create a schema on the fly
    assert make_schema_dict(schema, 'args', ['id', 'email']) == {
        'type': 'object',
        'additionalProperties': True,
        'properties': {
            'id': {'$ref': '#/definitions/id'},
            'email': {'$ref': '#/definitions/email'}
        }
    }

    # Should be able to make some of the names required.
    assert make_schema_dict(schema, 'args', ['id', 'email'], ['id']) == {
        'type': 'object',
        'additionalProperties': True,
        'properties': {
            'id': {'$ref': '#/definitions/id'},
            'email': {'$ref': '#/definitions/email'}
        },
        'required': ['id']
    }

    # Passing something weird should raise an error
    with pytest.raises(TypeError):
        assert make_schema_dict(schema, 'args', mock.sentinel.invalid)

    # Passing in an invalid name should raise a RefResolutionError
    with pytest.raises(jsonschema.exceptions.RefResolutionError):
        make_schema_dict(schema, 'args', 'bad')
    with pytest.raises(jsonschema.exceptions.RefResolutionError):
        make_schema_dict(schema, 'args', ['bad'])


def test_with_wraps_no_arguments():
    """It should raise a TypeError if called without arguments."""
    with pytest.raises(TypeError):
        with_wraps()


def test_with_wraps():
    """Make sure it works for a typical decorator use case."""
    s = mock.sentinel
    mock_func = mock.Mock()
    mock_wrapper = mock.Mock(return_value=s.return_value)
    mock_decorator = mock.Mock()
    mock_decorator.__name__ = 'mock_decorator'
    mock_decorator.return_value = mock_wrapper

    decorator = with_wraps(mock_decorator)
    wrapper = decorator(mock_func)
    assert wrapper._wraps == mock_func

    return_value = wrapper(s.arg1, s.arg2, kwarg1=s.kwarg1, kwarg2=s.kwarg2)
    assert return_value == s.return_value
    assert mock_wrapper.call_args_list == [
        mock.call(s.arg1, s.arg2, kwarg1=s.kwarg1, kwarg2=s.kwarg2)
    ]


def test_with_wraps_arguments():
    """
    Make sure it works for the slightly weirder case of a decorator that
    accepts arguments and in turn returns a decorator.
    """
    s = mock.sentinel
    mock_func = mock.Mock()
    mock_wrapper = mock.Mock(return_value=s.return_value)
    mock_decorator = mock.Mock()
    mock_decorator.__name__ = 'mock_decorator'
    mock_decorator.return_value = mock_wrapper
    mock_decorator_with_arguments = mock.Mock()
    mock_decorator_with_arguments.__name__ = 'mock_decorator_with_arguments'
    mock_decorator_with_arguments.return_value = mock_decorator

    wraps_decorator = with_wraps(arguments=True)
    decorator_generator = wraps_decorator(mock_decorator_with_arguments)
    decorator = decorator_generator(s.arg1, s.arg2, kwarg1=s.kwarg1,
                                    kwarg2=s.kwarg2)
    assert mock_decorator_with_arguments.call_args_list == [
        mock.call(s.arg1, s.arg2, kwarg1=s.kwarg1, kwarg2=s.kwarg2)
    ]

    wrapper = decorator(mock_func)
    assert mock_decorator.call_args_list == [mock.call(mock_func)]
    assert wrapper._wraps == mock_func

    return_value = wrapper(s.arg1, s.arg2, kwarg1=s.kwarg1, kwarg2=s.kwarg2)
    assert return_value == s.return_value
    assert mock_wrapper.call_args_list == [
        mock.call(s.arg1, s.arg2, kwarg1=s.kwarg1, kwarg2=s.kwarg2)
    ]


def test_with_wraps_missing_arguments():
    """
    It should raise a TypeError if someone accidentally decorates a decorator
    that takes arguments, but forgets to add arguments=True.
    """
    @with_wraps
    def my_decorator(arg1, arg2):
        pass
    with pytest.raises(TypeError):
        my_decorator(1, 2)
