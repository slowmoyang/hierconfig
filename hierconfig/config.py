import dataclasses
import inspect
from dataclasses import Field
from dataclasses import dataclass
from dataclasses import asdict
from dataclasses import MISSING
from dataclasses import make_dataclass
import argparse
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from argparse import Namespace
from pathlib import Path
import json
import typing
from typing import Any, Optional
from colorama import Fore
from colorama import Style
import yaml


class ColorfulHelpFormatter(ArgumentDefaultsHelpFormatter):

    def _format_action_invocation(self, action):
        """https://github.com/python/cpython/blob/v3.9.13/Lib/argparse.py#L551-L573"""
        if not action.option_strings:
            default = self._get_default_metavar_for_positional(action)
            metavar, = self._metavar_formatter(action, default)(1)
            return metavar
        else:
            parts = []
            if action.nargs == 0:
                option_strings = [f'{Fore.GREEN}{each}{Fore.RESET}' for each in action.option_strings]
                parts.extend(option_strings)
            else:
                default = self._get_default_metavar_for_optional(action)
                args_string = self._format_args(action, default)
                for option_string in action.option_strings:
                    parts.append(f'{Fore.GREEN}{option_string}{Fore.RESET} {Style.DIM}{args_string}{Style.NORMAL}')

            return ', '.join(parts)

    def _get_help_string(self, action):
        help_str = action.help
        if isinstance(help_str, str):
            if '%(default)' not in help_str:
                if action.default is not argparse.SUPPRESS:
                    default_nargs = (argparse.OPTIONAL, argparse.ZERO_OR_MORE)
                    if action.option_strings or action.nargs in default_nargs:
                        help_str += f' (default: {Fore.RED}%(default)s{Fore.RESET})'
        return help_str



@dataclass
class ConfigBase:

    @classmethod
    def from_args(cls, argv: Optional[list[str]] = None):
        parser = argparse.ArgumentParser(formatter_class=ColorfulHelpFormatter)
        cls._add_arg_from_cls(parser, cls, prefixes=[], seen=set())
        args = parser.parse_args(argv)
        config_dict = cls._convert_namespace_to_dict(args)
        return cls.from_dict(config_dict)

    @classmethod
    def _convert_namespace_to_dict(cls, namespace: Namespace):
        config = {}
        for key, value in vars(namespace).items():
            *prefixes, name = key.split('.')
            inner = config
            while len(prefixes) > 0:
                each = prefixes.pop(0)
                if each not in inner:
                    inner[each] = {}
                inner = inner[each]
            inner[name] = value
        return config

    @classmethod
    def _add_arg_from_cls(cls, parser, config_cls, prefixes, seen: set[str]):
        for field in dataclasses.fields(config_cls):
            if inspect.isclass(field.type) and issubclass(field.type, ConfigBase):
                new_prefixes = prefixes + [field.name]
                cls._add_arg_from_cls(parser, field.type, new_prefixes, seen)
            else:
                cls._add_arg_by_type(parser, field, prefixes, seen)

    @staticmethod
    def _get_metadata(field: Field, key: str, default=None):
        return field.metadata.get(key, default)

    @classmethod
    def _add_arg_by_type(cls, parser, field, prefixes: list[str], seen: set[str]):
        origin = typing.get_origin(field.type)

        if origin is None:
            if field.type is bool:
                cls._add_argument_bool(parser, field, prefixes, seen)
            else:
                cls._add_argument_default(parser, field, prefixes, seen)
        else:
            if origin is tuple:
                cls._add_argument_tuple(parser, field, prefixes, seen)
            elif origin is list:
                cls._add_argument_list(parser, field, prefixes, seen)
            else:
                cls._add_argument_default(parser, field, prefixes, seen)

    @staticmethod
    def _get_flag(prefixes: list[str], field: Field, seen: set[str]) -> str:
        name = field.name.replace('_', '-')
        if name in seen:
            assert len(prefixes) > 0, f'{name=}, {seen=}'
            name = '.'.join(prefixes + [name])
            assert name not in seen
        seen.add(name)
        flag = f'--' + name
        return flag

    @staticmethod
    def _get_dest(prefixes: list[str], field: Field) -> str:
        name = field.name
        if len(prefixes) > 0:
            name = '.'.join(prefixes + [name])
        return name

    @staticmethod
    def _get_default(field: Field):
        if field.default is not MISSING:
            default = field.default
        elif field.default_factory is not MISSING:
            default = field.default_factory()
        else:
            default = None
        return default

    @classmethod
    def _get_help(cls, field: Field) -> str:
        help = cls._get_metadata(field, 'help', ' ')
        help = typing.cast(str, help)
        help += f' (type={field.type.__name__})'
        return help

    @classmethod
    def _add_arg(cls, parser: ArgumentParser, field: Field,
                 prefixes: list[str], seen: set[str], **kwargs):
        try:
            flag = cls._get_flag(prefixes, field, seen)
            dest = cls._get_dest(prefixes, field)
            default = cls._get_default(field)
            type = kwargs.pop('type', field.type)
            help = cls._get_help(field)
            choices = cls._get_metadata(field, 'choices', default=None)
        except Exception as error:
            print(f'{field=} causes the following error.') # TODO warnings.warn
            raise error
        return parser.add_argument(flag, dest=dest, default=default, type=type,
                                   help=help, choices=choices, **kwargs)

    @classmethod
    def _add_argument_default(cls, parser: ArgumentParser, field: Field, prefixes: list[str], seen: set[str]):
        return cls._add_arg(parser, field, prefixes, seen)

    @classmethod
    def _add_argument_tuple(cls, parser: ArgumentParser, field: Field, prefixes: list[str], seen: set[str]):
        args = typing.get_args(field.type)
        assert len(set(args)) == 1, args
        nargs = len(args)
        return cls._add_arg(parser, field, prefixes, seen, nargs=nargs)

    @classmethod
    def _add_argument_list(cls, parser: ArgumentParser, field: Field, prefixes: list[str], seen: set[str]):
        args = typing.get_args(field.type)
        assert len(args) == 1, args
        return cls._add_arg(parser, field, prefixes, seen, nargs='+')

    @classmethod
    def _add_argument_bool(cls,
                           parser: ArgumentParser,
                           field: Field,
                           prefixes: list[str],
                           seen: set[str]
    ):
        """
        """
        assert field.type is bool, field.type
        assert field.default is not None, field.default
        action = argparse.BooleanOptionalAction
        flag = cls._get_flag(prefixes, field, seen)
        dest = cls._get_dest(prefixes, field)
        default = cls._get_default(field)
        help = cls._get_help(field)
        return parser.add_argument(
            flag,
            dest=dest,
            default=default,
            action=action,
            help=help
        )

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, config):
        for field in dataclasses.fields(cls):
            if is_config_class(field.type):
                config[field.name] = field.type.from_dict(config[field.name])
        return cls(**config)

    def to_json(self, path):
        with open(path, 'w') as stream:
            json.dump(self.to_dict(), stream, indent=4)

    @classmethod
    def from_json(cls, path):
        with open(path, 'r') as stream:
            config = json.load(stream)
        return cls.from_dict(config)

    def to_yaml(self, path):
        with open(path, 'w') as stream:
            yaml.dump(self.to_dict(), stream)

    @classmethod
    def from_yaml(cls, path):
        with open(path, 'r') as stream:
            config = yaml.safe_load(stream)
        return cls.from_dict(config)

    @classmethod
    def from_file(cls, path: typing.Union[str, Path]):
        path = Path(path)
        if path.suffix == '.json':
            loader = cls.from_json
        elif path.suffix == '.yaml':
            loader = cls.from_yaml
        else:
            raise RuntimeError(f'unknown file extension: {path.suffix}')
        return loader(path)

    def __str__(self):
        return json.dumps(self.to_dict(), indent=4)



def hierconfig(cls):
    """decorator"""
    fields = [(key, value) + ((getattr(cls, key), ) if hasattr(cls, key) else ())
              for key, value in cls.__annotations__.items()]
    return make_dataclass(cls.__name__, fields=fields, bases=(ConfigBase, cls))


def is_config_class(test_cls):
    return inspect.isclass(test_cls) and issubclass(test_cls, ConfigBase)


def config_field(help: Optional[str] = None,
                 choices: Optional[tuple[Any, ...]] = None,
                 metadata: dict = {},
                 **kwargs):
    if help is not None:
        metadata['help'] = help
    if choices is not None:
        metadata['choices'] = choices
    return dataclasses.field(metadata=metadata, **kwargs)
