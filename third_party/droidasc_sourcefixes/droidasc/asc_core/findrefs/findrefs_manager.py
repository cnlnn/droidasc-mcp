# Auth: MG1937
from .locator.insn_locator import InsnLocator
from .locator.field_locator import FieldLocator
from .locator.method_locator import MethodLocator
from .locator.string_locator import StringLocator
from .locator.type_locator import TypeLocator
from .scan.code_item_scan import CodeItemScanner
from .scan.class_def_item_scan import ClassDefItemScan


class FindRefManager:
    def __init__(self, dex, debug = False):
        self.dex = dex
        self.debug = debug
        self.str_locator = None
        self.type_locator = None
        self.method_locator = None
        self.field_locator = None
        self.insn_locator = None
        self.code_scanner = None
        self.class_def_item_scanner = None

    def _get_str_locator(self, build = False):
        locator = self.str_locator
        if locator is None:
            locator = StringLocator(self.dex)
            locator.set_debug(self.debug)
            self.str_locator = locator
        if build and not locator.parsed:
            locator._build_map()
        return locator

    def _get_type_locator(self, build = False):
        locator = self.type_locator
        if locator is None:
            locator = TypeLocator(self.dex)
            locator.set_debug(self.debug)
            locator.set_str_locator(self._get_str_locator(build))
            self.type_locator = locator
        if build and not locator.parsed:
            locator._build_map()
        return locator

    def _get_method_locator(self, build = False):
        locator = self.method_locator
        if locator is None:
            locator = MethodLocator(self.dex)
            locator.set_debug(self.debug)
            locator.set_str_locator(self._get_str_locator(True))
            locator.set_type_locator(self._get_type_locator(True))
            self.method_locator = locator
        if build and not locator.parsed:
            locator._build_map()
        return locator

    def _get_field_locator(self, build = False):
        locator = self.field_locator
        if locator is None:
            locator = FieldLocator(self.dex)
            locator.set_debug(self.debug)
            locator.set_str_locator(self._get_str_locator(True))
            locator.set_type_locator(self._get_type_locator(True))
            self.field_locator = locator
        if build and not locator.parsed:
            locator._build_map()
        return locator

    def _get_code_scanner(self):
        insn_locator = self.insn_locator
        if insn_locator is None:
            insn_locator = InsnLocator(self.dex)
            insn_locator.set_debug(self.debug)
            self.insn_locator = insn_locator
        if not insn_locator.parsed:
            insn_locator.parse()

        scanner = self.code_scanner
        if scanner is None:
            scanner = CodeItemScanner(insn_locator)
            self.code_scanner = scanner
        return scanner

    def _get_class_def_item_scanner(self):
        scanner = self.class_def_item_scanner
        if scanner is None:
            # precisly locate type id, no need to build string/type map
            scanner = ClassDefItemScan(self._get_type_locator(False))
            self.class_def_item_scanner = scanner
        return scanner

    # find struct: {"string" : "foo", "type" : "bar", "method" : {...}, "field" : {...}, "extends" : "Lfoo;"}
    # locate result will overwrite input find in-place, then scanner writes ref mids back into each key
    # extends writes class idx back into find and returns directly, dont scan code item
    def find_ref(self, find : dict, mark = False, group = False):
        if group:
            return self._find_ref_grouped(find, mark)
        # non-group contract: extends/impl are class-def lookups that short-circuit
        # the opcode scan, so a plain call sees only that subclass result
        if "extends" in find:
            find["extends"] = self._get_class_def_item_scanner().scan_extends(find["extends"])
            return find["extends"]
        if "impl" in find:
            find["impl"] = self._get_class_def_item_scanner().scan_implements(find["impl"])
            return find["impl"]

        # non-group keeps the original contract: located idxs are written back
        # into find in place, and if nothing is located every ref key becomes []
        refs, has_idx = self._collect_refs(find)
        find.update(refs)
        if not find:
            return
        if not has_idx:
            for type_ in find:
                find[type_] = []
            return []

        self._get_code_scanner().scan(find, mark)
        return self._get_code_scanner().mark_idx

    # group=True: every queried key comes back as one list in the result dict,
    # 1:1 with the input. extends/impl resolve the subclass set from class_def_item;
    # the rest are opcode references. Only ref keys ever enter the code-item scan.
    def _find_ref_grouped(self, find : dict, mark = False):
        result = {}
        if "extends" in find:
            result["extends"] = self._get_class_def_item_scanner().scan_extends(find["extends"])
        if "impl" in find:
            result["impl"] = self._get_class_def_item_scanner().scan_implements(find["impl"])

        refs, has_idx = self._collect_refs(find)
        if not has_idx:
            # no located idx anywhere -> every ref key is an empty list
            result.update({key: [] for key in refs})
            return result
        self._get_code_scanner().scan(refs, mark)
        result.update(refs)
        return result

    # locate each opcode-ref key into {type: idx_set}; returns the located keys
    # and whether any of them hit. find is not modified here.
    def _collect_refs(self, find : dict):
        refs = {}
        if "string" in find:
            refs["string"] = self._get_str_locator(True).locate(find["string"])
        if "type" in find:
            refs["type"] = self._get_type_locator(True).locate(find["type"])
        if "method" in find:
            refs["method"] = self._get_method_locator(True).locate(find["method"])
        if "field" in find:
            refs["field"] = self._get_field_locator(True).locate(find["field"])
        has_idx = any(refs.values())
        return refs, has_idx
