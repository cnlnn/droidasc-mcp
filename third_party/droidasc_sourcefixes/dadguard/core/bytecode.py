# Allows type hinting of types not-yet-declared
# in Python >= 3.7
# see https://peps.python.org/pep-0563/
from __future__ import annotations

from struct import pack
from typing import Union

from dadguard.core.androconf import CONF



def _PrintBanner():
    print_fct = CONF["PRINT_FCT"]
    print_fct("*" * 75 + "\n")


def _PrintSubBanner(title=None):
    print_fct = CONF["PRINT_FCT"]
    if title is None:
        print_fct("#" * 20 + "\n")
    else:
        print_fct("#" * 10 + " " + title + "\n")


def _PrintNote(note, tab=0):
    print_fct = CONF["PRINT_FCT"]
    note_color = CONF["COLORS"]["NOTE"]
    normal_color = CONF["COLORS"]["NORMAL"]
    print_fct(
        "\t" * tab + "{}# {}{}".format(note_color, note, normal_color) + "\n"
    )


def _Print(name, arg):
    """Print arg into a correct format"""
    buff = name + " "

    if type(arg).__name__ == 'int':
        buff += "0x%x" % arg
    elif type(arg).__name__ == 'long':
        buff += "0x%x" % arg
    elif type(arg).__name__ == 'str':
        buff += "%s" % arg

    print(buff)


def _PrintDefault(msg):
    print_fct = CONF["PRINT_FCT"]
    print_fct(msg)


# [slim] Removed dead graph/JSON/pretty-print exporters that no path in the
# decompile/findrefs pipeline ever calls: PrettyShow / PrettyShowEx /
# _PrintXRef / _PrintDRef / _colorize_operands / _get_operand_html /
# method2dot / method2format / method2png / method2jpg / vm2json / TmpBlock /
# method2json[_direct|_undirect]. These pulled in pydot/graphviz/json/textwrap
# and the terminal color machinery for output nobody consumes here. 20260801


def object_to_bytes(obj: Union[str, bool, int, bytearray]) -> bytearray:
    """
    Convert a object to a bytearray or call `get_raw()` of the object
    if no useful type was found.

    :param obj: the object to convert
    :returns: the bytes
    """
    if isinstance(obj, str):
        return bytearray(obj, "UTF-8")
    if isinstance(obj, bool):
        return bytearray()
    if isinstance(obj, int):
        return pack("<L", obj)
    if obj is None:
        return bytearray()
    if isinstance(obj, bytearray):
        return obj

    return obj.get_raw()


def FormatClassToPython(i: str) -> str:
    """
    Transform a typed class name into a form which can be used as a python
    attribute

    Example:

        >>> FormatClassToPython('Lfoo/bar/foo/Barfoo$InnerClass;')
        'Lfoo_bar_foo_Barfoo_InnerClass'

    :param i: classname to transform
    :returns: the formatted string
    """
    i = i[:-1]
    i = i.replace("/", "_")
    i = i.replace("$", "_")

    return i


def get_package_class_name(name: str) -> tuple[str, str]:
    """
    Return package and class name in a java variant from a typed variant name.

    If no package could be found, the package is an empty string.

    If the name is an array type, the array is discarded.

    Example:

        >>> get_package_class_name('Ljava/lang/Object;')
        ('java.lang', 'Object')
        >>> get_package_class_name('[[Ljava/lang/Object;')
        ('java.lang', 'Object')
        >>> get_package_class_name('LSomeClass;')
        ('', 'SomeClass')

    :param name: the name
    :returns: the formatted package class name
    """
    # name is MUTF8, so make sure we get the string variant
    name = str(name)
    if name[-1] != ';':
        raise ValueError(
            "The name '{}' does not look like a typed name!".format(name)
        )

    # discard array types, there might be many...
    name = name.lstrip('[')

    if name[0] != 'L':
        raise ValueError(
            "The name '{}' does not look like a typed name!".format(name)
        )

    name = name[1:-1]
    if '/' not in name:
        return '', name

    package, clsname = name.rsplit('/', 1)
    package = package.replace('/', '.')

    return package, clsname


def FormatNameToPython(i: str) -> str:
    """
    Transform a (method) name into a form which can be used as a python
    attribute

    Example:

        >>> FormatNameToPython('<clinit>')
        'clinit'

    :param i: name to transform
    :returns: the transformed name
    """

    i = i.replace("<", "")
    i = i.replace(">", "")
    i = i.replace("$", "_")

    return i


def FormatDescriptorToPython(i: str) -> str:
    """
    Format a descriptor into a form which can be used as a python attribute

    Example:

        >>> FormatDescriptorToPython('(Ljava/lang/Long; Ljava/lang/Long; Z Z)V')
        'Ljava_lang_LongLjava_lang_LongZZV

    :param i: name to transform
    :returns: the formatted descriptor string
    """

    i = i.replace("/", "_")
    i = i.replace(";", "")
    i = i.replace("[", "")
    i = i.replace("(", "")
    i = i.replace(")", "")
    i = i.replace(" ", "")
    i = i.replace("$", "")

    return i


class Node:
    def __init__(self, n, s):
        self.id = n
        self.title = s
        self.children = []
