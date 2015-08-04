import jsonschema
from jsonschema.validators import validator_for


class Schema(object):

    """A wrapper around a JSON schema dict.

    This wrapper provides a resolver and a validator for the given schema, so
    they don't need to be created elsewhere. It can be useful for cases where
    a schema uses a custom resolver (which they do for Doctor).

    :param dict raw_schema: The actual JSON schema dictionary.
    :param str base_uri: The base URI for this schema. When created from a
        file, this is set to the directory the schema was contained in, so that
        relative references to other files from within the schema work as
        expected. If unspecified, defaults to the value of 'id' in the root of
        raw_schema, or blank.
    :param jsonschema.RefResolver ref_resolver: A resolver to use for this
        schema. If unspecified, a new resolver will be created using
        resolver_cls.
    :param class resolver_cls: The class to use for the resolver, if creating
        a new resolver on the fly. Defaults to :class:`jsonschema.RefResolver`.
    :param jsonschema.Validator validator: A validator to use for this schema.
        If unspecified, a new validator will be created using validator_cls.
    :param class validator_cls: The class to use for the validator, if creating
        a new validator on the fly. Defaults to the value returned by
        :func:`jsonschema.validators.validator_for()` for the given schema.
    """

    def __init__(self, raw_schema, base_uri=None, resolver=None,
                 resolver_cls=None, validator=None, validator_cls=None):
        self.raw_schema = raw_schema

        if resolver is None:
            if resolver_cls is None:
                resolver_cls = jsonschema.RefResolver
            if base_uri is None:
                base_uri = self.raw_schema.get(u'id', u'')
            resolver = resolver_cls(base_uri, self.raw_schema)
        self.resolver = resolver

        if validator is None:
            if validator_cls is None:
                validator_cls = validator_for(self.raw_schema)
            validator = validator_cls(self.raw_schema, resolver=self.resolver)
        self.validator = validator

    def resolve(self, ref):
        """Resolve a reference within the schema.

        :param str ref: Reference to resolve. This is usually a URI fragment,
            like '#/definitions/foo'.
        :returns: The resolved reference.
        :raises jsonschema.RefResolutionError:
        """
        return self.resolver.resolve(ref)
