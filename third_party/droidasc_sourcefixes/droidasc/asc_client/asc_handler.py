import copy
import importlib.util
import os
import sys
import types
from collections import defaultdict


_DexManager = None
_FindRefManager = None
_decompile_dex_bytes = None
_decompile_dex_bytes_with_metadata = None
_DEX = None


def _install_pure_python_mutf8_shim():
    if "mutf8.cmutf8" in sys.modules:
        return

    # Some mutf8 distributions ship the Python implementation but not the
    # optional native module imported by Androguard. Mirror only its two APIs.
    pkg_spec = importlib.util.find_spec("mutf8")
    if pkg_spec is None or not pkg_spec.submodule_search_locations:
        return

    pkg_dir = pkg_spec.submodule_search_locations[0]
    py_impl = os.path.join(pkg_dir, "mutf8.py")
    mod_spec = importlib.util.spec_from_file_location("_asc_client_mutf8_py", py_impl)
    if mod_spec is None or mod_spec.loader is None:
        return

    module = importlib.util.module_from_spec(mod_spec)
    mod_spec.loader.exec_module(module)

    shim = types.ModuleType("mutf8.cmutf8")
    shim.decode_modified_utf8 = module.decode_modified_utf8
    shim.encode_modified_utf8 = module.encode_modified_utf8
    sys.modules["mutf8.cmutf8"] = shim


def _lazy_import():
    global _DexManager, _FindRefManager, _decompile_dex_bytes, _decompile_dex_bytes_with_metadata, _DEX
    if _DexManager is not None:
        return

    # Core/decompiler imports are large and optional for listclass/findrefs
    # startup. Resolve them once, only when source decompilation is requested.
    _install_pure_python_mutf8_shim()
    from droidasc.asc_core.core.dex.dex_manager import DexManager
    from droidasc.asc_core.findrefs.findrefs_manager import FindRefManager
    from droidasc.asc_core.utils.tinydex import DEX
    from droidasc.asc_core.utils.decompiler import decompile_dex_bytes, decompile_dex_bytes_with_metadata

    _DexManager = DexManager
    _FindRefManager = FindRefManager
    _decompile_dex_bytes = decompile_dex_bytes
    _decompile_dex_bytes_with_metadata = decompile_dex_bytes_with_metadata
    _DEX = DEX


class AscHandler:
    def __init__(self, debug : bool = False):
        self.debug = debug

    def getclass(self, dex_buf : bytes, dalvik_class : str) -> str:
        _lazy_import()
        manager = _DexManager(memoryview(dex_buf), debug=self.debug)
        new_dex_bytes = manager.extract_and_rebuild(dalvik_class)
        return _decompile_dex_bytes(new_dex_bytes, dalvik_class)

    def getclass_with_metadata(self, dex_buf : bytes, dalvik_class : str):
        _lazy_import()
        manager = _DexManager(memoryview(dex_buf), debug=self.debug)
        new_dex_bytes = manager.extract_and_rebuild(dalvik_class)
        return _decompile_dex_bytes_with_metadata(new_dex_bytes, dalvik_class)

    def _format_method(self, dex, midx : int, include_descriptor : bool = False) -> str:
        method = dex.methods[midx]
        ret = f"{method.cls.fullname}->{method.name}"
        if not include_descriptor:
            return ret
        proto = method.prototype
        descriptor = "(" + "".join(item.descriptor for item in proto.parameters_type) + ")"
        descriptor += dex.get_type(proto.return_type_idx).descriptor
        return ret + descriptor

    def _format_matched_name(
        self, dex, find_type : str, idx : int, include_descriptor : bool = False,
    ) -> str:
        if find_type == "string":
            return str(dex.strings[idx])
        if find_type == "type":
            return dex.types[idx].descriptor
        if find_type == "method":
            return self._format_method(dex, idx, include_descriptor=include_descriptor)
        field = dex.fields[idx]
        ret = f"{field.cls.fullname}->{field.name}"
        return f"{ret}:{field.type.descriptor}" if include_descriptor else ret

    def findrefs(self, dex_name : str, dex_buf : bytes, find_type : str, find : dict, aggregate : bool = True) -> list:
        from droidasc.asc_core.findrefs.findrefs_manager import FindRefManager
        from droidasc.asc_core.utils.tinydex import DEX

        dex = DEX.parse(memoryview(dex_buf), dex_name)
        ref_manager = FindRefManager(dex)
        # extends/impl short-circuit in find_ref: they return class indexes, not
        # containing-method indexes, so format them directly. find must be copied
        # too -- find_ref rewrites the target key in place and workers reuse it.
        if find_type in ("extends", "impl"):
            target = find[find_type]
            # scan_extends/scan_implements hand back type_id indexes (a class's
            # class_idx field in class_def_item), not class_def positions, so
            # resolve each directly through the type table.
            class_idxs = ref_manager.find_ref(copy.deepcopy(find), True)
            verb = "extends" if find_type == "extends" else "implements"
            return [
                f"{dex_name} | {dex.get_type(class_idx).descriptor} {verb} {target}"
                for class_idx in class_idxs
            ]
        # find_ref rewrites the selected query list with containing method
        # indexes. Keep the caller's query reusable across DEX workers.
        query = copy.deepcopy(find)
        matched_idxs = ref_manager.find_ref(query, True)
        mids = query[find_type]
        if not aggregate:
            ret = []
            occurrences = defaultdict(int)
            # matched_idxs and mids are parallel arrays. One matched item may
            # belong to several methods, hence the list normalization below.
            for i in range(len(mids)):
                midx = mids[i]
                if midx is None:
                    continue
                idx = matched_idxs[i]
                if isinstance(midx, list):
                    midxs = midx
                else:
                    midxs = [midx]
                matched = self._format_matched_name(
                    dex, find_type, idx, include_descriptor=True
                )
                for mid in midxs:
                    key = (mid, idx)
                    occurrence = occurrences[key]
                    occurrences[key] += 1
                    ret.append(
                        f"{dex_name} | {self._format_method(dex, mid, include_descriptor=True)} | "
                        f"matched=({matched}) | occurrence={occurrence}"
                    )
            return ret

        grouped = defaultdict(set)
        # Aggregate mode collapses repeated targets per containing method while
        # preserving deterministic method/target ordering in the output.
        for i in range(len(mids)):
            midx = mids[i]
            if midx is None:
                continue
            idx = matched_idxs[i]
            if isinstance(midx, list):
                midxs = midx
            else:
                midxs = [midx]
            for mid in midxs:
                grouped[mid].add(idx)

        ret = []
        for mid in sorted(grouped):
            matched = "; ".join(
                self._format_matched_name(dex, find_type, idx)
                for idx in sorted(grouped[mid])
            )
            ret.append(
                f"{dex_name} | {self._format_method(dex, mid)} | matched=({matched})"
            )
        return ret
