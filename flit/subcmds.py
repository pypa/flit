import argparse
import importlib
import sys

def load_obj(objref):
    """Load an object from an entry point style object reference

    'mod.submod:obj.attr'
    """
    modname, qualname_separator, qualname = objref.partition(':')
    obj = importlib.import_module(modname)
    if qualname_separator:
        for attr in qualname.split('.'):
            obj = getattr(obj, attr)
    return obj

class Subcommand:
    def __init__(self, name, *, func, help):
        self.name = name
        self.func = func
        self.help = help

    def run(self, extra_argv):
        if isinstance(self.func, str):
            self.func = load_obj(self.func)
        return self.func(extra_argv)

class SubcommandArgumentParser(argparse.ArgumentParser):
    def add_subcommands(self, subcommands):
        self.add_argument('subcommand_and_args', nargs=argparse.REMAINDER)
        self.__subcommands = subcommands


    def format_help(self):
        special_options = self._optionals._group_actions
        special_options_names = []
        for so in special_options:
            if so.help is not argparse.SUPPRESS:
                special_options_names.extend(so.option_strings)

        # usage
        lines = [
            "usage: {prog} [{options}]".format(prog=self.prog,
               options=" | ".join(special_options_names)),
            "   or: {prog} <command>".format(prog=self.prog),
            ""
        ]

        # special optional args
        formatter = self._get_formatter()
        formatter.start_section("Special options")
        formatter.add_arguments(self._optionals._group_actions)
        formatter.end_section()
        lines.append(formatter.format_help())

        # subcommands
        lines += ["Commands:"]
        for sc in self.__subcommands:
            if sc.help is not argparse.SUPPRESS:
                s = "  {:<12} {}".format(sc.name, sc.help)
                lines.append(s)

        return "\n".join(lines) + "\n"

    def dispatch_subcommand(self, parsed_args):
        if not parsed_args.subcommand_and_args:
            self.print_help()
            sys.exit(2)

        subcmd, *extra_argv = parsed_args.subcommand_and_args
        for sc in self.__subcommands:
            if sc.name == subcmd:
                sys.exit(sc.run(extra_argv))

        print("Unknown command {!r}".format(subcmd))
        print("  Available commands are: ",
              ", ".join(sc.name for sc in self.__subcommands))
        sys.exit(2)
