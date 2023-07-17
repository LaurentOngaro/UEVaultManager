# coding=utf-8
"""
Class definitions for:
- HiddenAliasSubparsersAction: Subclass of argparse._SubParsersAction that hides aliases from the help output.
"""
import argparse


# noinspection PyUnresolvedReferences,PyProtectedMember
class HiddenAliasSubparsersAction(argparse._SubParsersAction):
    """
    Subclass of argparse._SubParsersAction that hides aliases from the help output.
    """
    def add_parser(self, name: str, **kwargs):
        """
        Add a parser to the set of parsers for this action.
        :param name: Name of the parser.
        :param kwargs: Keyword arguments.
        :return: The created parser.
        """
        # set prog from the existing prefix
        if kwargs.get('prog') is None:
            kwargs['prog'] = f'{self._prog_prefix} {name}'

        aliases = kwargs.pop('aliases', ())
        hide_aliases = kwargs.pop('hide_aliases', False)

        # create a pseudo-action to hold the choice help
        if 'help' in kwargs:
            help_value = kwargs.pop('help')
            _aliases = None if hide_aliases else aliases
            choice_action = self._ChoicesPseudoAction(name, _aliases, help_value)
            self._choices_actions.append(choice_action)

        # create the parser and add it to the map
        parser = self._parser_class(**kwargs)
        self._name_parser_map[name] = parser

        # make parser available under aliases also
        for alias in aliases:
            self._name_parser_map[alias] = parser

        return parser
