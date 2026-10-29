import zipfile
import sys
import types


class _DummyLogger:
    def __getattr__(self, _name):
        return self._noop

    @staticmethod
    def _noop(*_args, **_kwargs):
        pass


def _dummy_axml_logger():
    dummy_logger = _DummyLogger()
    logging_module = types.ModuleType("axml.helper.logging")
    logging_module.LOGGER = dummy_logger
    # axml imports this optional logging module by its fully qualified name.
    # Install the stub before importing AXMLPrinter to silence library output.
    sys.modules["axml.helper.logging"] = logging_module

    # axml modules cache LOGGER with a module-level import.
    for module_name, module in tuple(sys.modules.items()):
        if module_name.startswith("axml.") and getattr(module, "LOGGER", None):
            module.LOGGER = dummy_logger
    return dummy_logger


def get_manifest_xml(apk_path : str, pretty : bool = True) -> str:
    with zipfile.ZipFile(apk_path) as zf:
        manifest_data = zf.read("AndroidManifest.xml")

    _dummy_axml_logger()
    from axml.axml import AXMLPrinter

    axml = AXMLPrinter(manifest_data)
    if not axml.is_valid():
        raise ValueError("AndroidManifest.xml is not a valid binary XML")
    return axml.get_xml(pretty=pretty).decode("utf-8", errors="replace")
