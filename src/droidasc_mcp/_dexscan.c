#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdint.h>
#include <string.h>
#include <limits.h>
#ifdef _WIN32
#include <windows.h>
#else
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#endif

static uint16_t u16(const unsigned char *p) {
    return (uint16_t)p[0] | ((uint16_t)p[1] << 8);
}

static uint32_t u32(const unsigned char *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static int append(PyObject *rows, Py_ssize_t position, Py_ssize_t address,
                  int opcode, Py_ssize_t count) {
    PyObject *row = Py_BuildValue("(nnin)", position, address, opcode, count);
    int status;
    if (!row) return -1;
    status = PyList_Append(rows, row);
    Py_DECREF(row);
    return status;
}

/* Shared checked cursor for row emission and allocation-free candidate selection. */
static int decode(const unsigned char *data, const unsigned char *widths,
                  const unsigned char *mask, Py_ssize_t position, Py_ssize_t end,
                  int version, int fields, int incoming, int pool,
                  unsigned int *opcode, uint64_t *bytes, int *special) {
    unsigned int op, width;
    int reference;
    if (end - position < 2) return -1;
    op = data[position];
    width = widths[op];
    if (!width || (op >= 0xfa && version < (op >= 0xfe ? 39 : 38))) return -1;
    *bytes = (uint64_t)width * 2;
    *special = 0;
    if (op == 0 && data[position + 1]) {
        unsigned int kind = data[position + 1], size;
        if (position % 4 || kind > 3 || end - position < (kind == 3 ? 8 : 4)) return -1;
        size = u16(data + position + 2);
        if (kind == 1) *bytes = 8 + (uint64_t)size * 4;
        else if (kind == 2) *bytes = 4 + (uint64_t)size * 8;
        else {
            if (size != 1 && size != 2 && size != 4 && size != 8) return -1;
            *bytes = 8 + (((uint64_t)size * u32(data + position + 4) + 1) / 2) * 2;
        }
        *special = 1;
    }
    if (*bytes > (uint64_t)(end - position)) return -1;
    reference = fields ? (op >= 0x52 && op <= 0x6d) :
        ((op >= 0x6e && op <= 0x72) || (op >= 0x74 && op <= 0x78) || op == 0xfa || op == 0xfb);
    if (reference) {
        unsigned int index;
        if (*bytes < 4) return -1;
        index = u16(data + position + 2);
        if ((uint64_t)index >= (uint64_t)pool) return -1;
        if (!incoming || mask[index]) *special = 1;
    }
    if (op >= 0xfa && op <= 0xfe) *special = 1;
    *opcode = op;
    return 0;
}

/* Buffers remain owned by Python; no pointer survives this call. All lengths
 * and payload products are checked before pointer arithmetic or operand reads. */
static PyObject *scan(PyObject *self, PyObject *args) {
    PyObject *data_obj, *width_obj, *mask_obj, *rows;
    char *raw, *width_raw, *mask_raw;
    const unsigned char *data, *widths, *mask;
    Py_ssize_t length, width_length, mask_length, code, start, end, position, resume = 0, skipped = 0;
    int version, fields, incoming, pool;
    (void)self;
    if (!PyArg_ParseTuple(args, "OniOOiii|n", &data_obj, &code, &version,
                          &width_obj, &mask_obj, &fields, &incoming, &pool, &resume)) return NULL;
    if (PyBytes_AsStringAndSize(data_obj, &raw, &length) < 0 ||
        PyBytes_AsStringAndSize(width_obj, &width_raw, &width_length) < 0 ||
        PyBytes_AsStringAndSize(mask_obj, &mask_raw, &mask_length) < 0) return NULL;
    data = (const unsigned char *)raw;
    widths = (const unsigned char *)width_raw;
    mask = (const unsigned char *)mask_raw;
    if (width_length != 256 || mask_length != 65536 || pool < 0 ||
        code < 0 || code % 4 || code > length || length - code < 16) {
        PyErr_SetString(PyExc_ValueError, "Invalid DEX scanner arguments or code header");
        return NULL;
    }
    start = code + 16;
    if ((uint64_t)u32(data + code + 12) * 2 > (uint64_t)(length - start)) {
        PyErr_SetString(PyExc_ValueError, "DEX code item exceeds file bounds");
        return NULL;
    }
    end = start + (Py_ssize_t)u32(data + code + 12) * 2;
    if (resume && (resume < start || resume > end || resume % 2)) {
        PyErr_SetString(PyExc_ValueError, "Invalid DEX scan continuation");
        return NULL;
    }
    rows = PyList_New(0);
    if (!rows) return NULL;
    position = resume ? resume : start;
    while (position < end) {
        unsigned int op;
        int special;
        uint64_t bytes;
        if (decode(data, widths, mask, position, end, version, fields, incoming, pool,
                   &op, &bytes, &special) < 0) goto invalid;
        skipped++;
        if (special) {
            if (append(rows, position, (position - start) / 2, (int)op, skipped) < 0)
                goto failed;
            skipped = 0;
        }
        position += (Py_ssize_t)bytes;
        /* Keep dense methods bounded too; the wrapper resumes at this exact
         * checked boundary, retaining the original code-unit address base. */
        if (PyList_Size(rows) >= 1024 && position < end) {
            if (append(rows, position, (position - start) / 2, -2, 0) < 0) goto failed;
            return rows;
        }
    }
    if (skipped && append(rows, end, (end - start) / 2, -1, skipped) < 0) goto failed;
    return rows;
invalid:
    PyErr_SetString(PyExc_ValueError, "Unknown, unavailable or truncated DEX instruction/payload/index");
failed:
    Py_DECREF(rows);
    return NULL;
}

static int leb(const unsigned char *data, Py_ssize_t length, Py_ssize_t *position, uint32_t *value) {
    unsigned int shift;
    *value = 0;
    for (shift = 0; shift < 35; shift += 7) {
        unsigned int byte;
        if (*position >= length) return -1;
        byte = data[(*position)++];
        if (shift == 28 && byte > 15) return -1;
        *value |= (uint32_t)(byte & 127) << shift;
        if (byte < 128) return 0;
    }
    return -1;
}

/* Decode one class, not the whole APK. Separate bitmaps catch duplicate IDs
 * across static/instance fields and direct/virtual methods respectively. */
static PyObject *members(PyObject *self, PyObject *args) {
    PyObject *data_obj, *fields = NULL, *methods = NULL, *result = NULL;
    char *raw;
    const unsigned char *data;
    unsigned char seen[2][8192] = {{0}};
    Py_ssize_t length, position;
    uint32_t sizes[4], field_pool, method_pool;
    unsigned int group;
    uint64_t total = 0;
    (void)self;
    if (!PyArg_ParseTuple(args, "OnII", &data_obj, &position, &field_pool, &method_pool)) return NULL;
    if (PyBytes_AsStringAndSize(data_obj, &raw, &length) < 0) return NULL;
    data = (const unsigned char *)raw;
    if (position < 0 || position >= length || field_pool > 65536 || method_pool > 65536)
        goto invalid_members;
    for (group = 0; group < 4; group++) {
        if (leb(data, length, &position, &sizes[group]) < 0) goto invalid_members;
        total += sizes[group];
    }
    if (total > (uint64_t)field_pool + method_pool) goto invalid_members;
    fields = PyList_New(0);
    methods = PyList_New(0);
    if (!fields || !methods) goto failed_members;
    for (group = 0; group < 4; group++) {
        uint32_t index = 0, i;
        for (i = 0; i < sizes[group]; i++) {
            uint32_t diff, flags, code;
            PyObject *row;
            unsigned int method = group >= 2;
            if (leb(data, length, &position, &diff) < 0 || diff > UINT32_MAX - index ||
                leb(data, length, &position, &flags) < 0) goto invalid_members;
            index += diff;
            if (index >= (method ? method_pool : field_pool) ||
                seen[method][index >> 3] & (1 << (index & 7))) goto invalid_members;
            seen[method][index >> 3] |= 1 << (index & 7);
            if (method) {
                if (leb(data, length, &position, &code) < 0) goto invalid_members;
                row = Py_BuildValue("(III)", index, flags, code);
            } else row = Py_BuildValue("(II)", index, flags);
            if (!row) goto failed_members;
            if (PyList_Append(method ? methods : fields, row) < 0) {
                Py_DECREF(row);
                goto failed_members;
            }
            Py_DECREF(row);
        }
    }
    result = PyTuple_Pack(2, fields, methods);
    goto failed_members;
invalid_members:
    PyErr_SetString(PyExc_ValueError, "Invalid, duplicate or truncated DEX class data");
failed_members:
    Py_XDECREF(fields);
    Py_XDECREF(methods);
    return result;
}

static int select_code(const unsigned char *data, Py_ssize_t length,
                       Py_ssize_t index, Py_ssize_t code, Py_ssize_t method_offset,
                       Py_ssize_t strings, Py_ssize_t protos,
                       const unsigned char *widths, const unsigned char *mask,
                       int version, int fields, int pool, int access, int select_dynamic,
                       unsigned long long *instructions, unsigned long long *dynamic,
                       unsigned long long *without) {
    Py_ssize_t position, end;
    int wanted = 0;
    if (index < 0 || index >= (length - method_offset) / 8) return -1;
    if (u32(data + method_offset + index * 8 + 4) >= (uint64_t)strings ||
        u16(data + method_offset + index * 8 + 2) >= (uint64_t)protos) return -1;
    if (!code) { (*without)++; return 0; }
    if (code < 0 || code % 4 || code > length || length - code < 16) return -1;
    position = code + 16;
    if ((uint64_t)u32(data + code + 12) * 2 > (uint64_t)(length - position)) return -1;
    end = position + (Py_ssize_t)u32(data + code + 12) * 2;
    while (position < end) {
        unsigned int op;
        uint64_t bytes;
        int special;
        if (decode(data, widths, mask, position, end, version, fields, 1, pool,
                   &op, &bytes, &special) < 0) return -1;
        (*instructions)++;
        if (op >= 0xfa && op <= 0xfe) { (*dynamic)++; wanted |= select_dynamic; }
        if (special && (fields ? (op >= 0x52 && op <= 0x6d) :
            ((op >= 0x6e && op <= 0x72) || (op >= 0x74 && op <= 0x78) || op == 0xfa || op == 0xfb))) {
            int read = (op >= 0x52 && op <= 0x58) || (op >= 0x60 && op <= 0x66);
            if (!fields || !access || access == (read ? 1 : 2)) wanted = 1;
        }
        position += (Py_ssize_t)bytes;
    }
    return wanted;
}

typedef struct {
    const unsigned char *data, *widths, *mask, *callers;
    Py_ssize_t length, method_offset, strings, protos;
    unsigned int field_pool, method_pool;
    int version, fields, access;
    unsigned long long count, instructions, dynamic, without;
    uint32_t *seen, generation;
} ClassSelection;

static int parse_class_selection(PyObject *args, int bulk, ClassSelection *scan,
                                 Py_ssize_t *cls, PyObject **directory) {
    PyObject *data_obj, *widths, *mask, *callers = NULL;
    char *raw, *width_raw, *mask_raw, *caller_raw;
    Py_ssize_t width_length, mask_length, caller_length;
    if (bulk) {
        if (!PyArg_ParseTuple(args, "OOiOOiIInnni|O", &data_obj, directory, &scan->version,
                             &widths, &mask, &scan->fields, &scan->field_pool, &scan->method_pool,
                             &scan->method_offset, &scan->strings, &scan->protos, &scan->access,
                             &callers)) return -1;
    } else if (!PyArg_ParseTuple(args, "OniOOiIInnni|O", &data_obj, cls, &scan->version,
                                &widths, &mask, &scan->fields, &scan->field_pool, &scan->method_pool,
                                &scan->method_offset, &scan->strings, &scan->protos, &scan->access,
                                &callers)) return -1;
    if (PyBytes_AsStringAndSize(data_obj, &raw, &scan->length) < 0 ||
        PyBytes_AsStringAndSize(widths, &width_raw, &width_length) < 0 ||
        PyBytes_AsStringAndSize(mask, &mask_raw, &mask_length) < 0) return -1;
    scan->data = (const unsigned char *)raw;
    scan->widths = (const unsigned char *)width_raw;
    scan->mask = (const unsigned char *)mask_raw;
    if (callers) {
        if (PyBytes_AsStringAndSize(callers, &caller_raw, &caller_length) < 0) return -1;
        if (caller_length != 65536 || scan->fields) {
            PyErr_SetString(PyExc_ValueError, "Invalid DEX graph caller mask");
            return -1;
        }
        scan->callers = (const unsigned char *)caller_raw;
    }
    if (scan->method_offset < 0 || scan->method_offset > scan->length ||
        scan->method_pool > (uint64_t)(scan->length-scan->method_offset)/8 ||
        scan->field_pool > 65536 || scan->method_pool > 65536 || scan->strings < 0 || scan->protos < 0 ||
        width_length != 256 || mask_length != 65536 || scan->fields < 0 || scan->fields > 1 ||
        scan->access < 0 || scan->access > 2) {
        PyErr_SetString(PyExc_ValueError, "Invalid DEX selection buffers or tables");
        return -1;
    }
    return 0;
}

/* Both entry points share the checked cursor. Nonmatching methods never become
 * Python tuples, but their metadata and every instruction are still validated. */
static int select_class_rows(ClassSelection *scan, Py_ssize_t cls,
                             PyObject *selected, PyObject *definitions) {
    const unsigned char *data = scan->data;
    Py_ssize_t length = scan->length, position;
    unsigned char seen[2][8192];
    uint32_t field_pool = scan->field_pool, method_pool = scan->method_pool, sizes[4];
    unsigned int group;
    uint64_t total = 0;
    if (cls < 0 || cls % 4 || cls > length || length - cls < 32)
        goto invalid_class_select;
    position = u32(data + cls + 24);
    if (!position) return 0;
    if (position >= length) goto invalid_class_select;
    if (!scan->seen) memset(seen, 0, sizeof(seen));
    for (group = 0; group < 4; group++) {
        if (leb(data, length, &position, &sizes[group]) < 0) goto invalid_class_select;
        total += sizes[group];
    }
    if (total > (uint64_t)field_pool + method_pool) goto invalid_class_select;
    for (group = 0; group < 4; group++) {
        uint32_t index = 0, i;
        unsigned int method = group >= 2;
        for (i = 0; i < sizes[group]; i++) {
            uint32_t diff, flags, code;
            PyObject *row;
            int wanted;
            if (leb(data, length, &position, &diff) < 0 || diff > UINT32_MAX-index ||
                leb(data, length, &position, &flags) < 0) goto invalid_class_select;
            index += diff;
            if (index >= (method ? method_pool : field_pool)) goto invalid_class_select;
            if (scan->seen) {
                uint32_t *stamp = scan->seen + (method ? field_pool : 0) + index;
                if (*stamp == scan->generation) goto invalid_class_select;
                *stamp = scan->generation;
            } else {
                if (seen[method][index >> 3] & (1 << (index & 7))) goto invalid_class_select;
                seen[method][index >> 3] |= 1 << (index & 7);
            }
            if ((scan->fields ? !method : method) && scan->mask[index]) {
                row = PyLong_FromUnsignedLong(index);
                if (!row) return -1;
                if (PyList_Append(definitions,row) < 0) { Py_DECREF(row); return -1; }
                Py_DECREF(row);
            }
            if (!method) continue;
            if (leb(data, length, &position, &code) < 0) goto invalid_class_select;
            scan->count++;
            wanted = select_code(data, length, index, code, scan->method_offset, scan->strings,
                                 scan->protos, scan->widths, scan->mask, scan->version,
                                 scan->fields, scan->fields ? field_pool : method_pool, scan->access,
                                 scan->callers == NULL,
                                 &scan->instructions, &scan->dynamic, &scan->without);
            if (wanted < 0) goto invalid_class_select;
            if (scan->callers && scan->callers[index]) wanted = 1;
            if (wanted) {
                row = Py_BuildValue("(III)", index, flags, code);
                if (!row) return -1;
                if (PyList_Append(selected,row) < 0) { Py_DECREF(row); return -1; }
                Py_DECREF(row);
            }
        }
    }
    return 0;
invalid_class_select:
    PyErr_SetString(PyExc_ValueError, "Invalid DEX class data, method metadata or instruction");
    return -1;
}

static PyObject *select_class(PyObject *self, PyObject *args) {
    ClassSelection scan = {0};
    Py_ssize_t cls = 0;
    PyObject *selected = NULL, *definitions = NULL, *result = NULL;
    (void)self;
    if (parse_class_selection(args, 0, &scan, &cls, NULL) < 0) return NULL;
    selected = PyList_New(0);
    definitions = PyList_New(0);
    if (!selected || !definitions || select_class_rows(&scan, cls, selected, definitions) < 0)
        goto failed_class_select;
    result = Py_BuildValue("OOKKKK", selected, definitions, scan.count, scan.instructions,
                           scan.dynamic, scan.without);
failed_class_select:
    Py_XDECREF(selected);
    Py_XDECREF(definitions);
    return result;
}

static PyObject *select_classes(PyObject *self, PyObject *args) {
    ClassSelection scan = {0};
    PyObject *directory = NULL, *selected = NULL, *definitions = NULL, *matches = NULL, *result = NULL;
    Py_ssize_t i;
    (void)self;
    if (parse_class_selection(args, 1, &scan, NULL, &directory) < 0) return NULL;
    if (!PyList_Check(directory)) {
        PyErr_SetString(PyExc_ValueError, "Invalid DEX selection directory");
        return NULL;
    }
    /* A bounded per-directory stamp table avoids clearing 16 KiB for every
     * class. Single-class callers retain the small independent bitset path. */
    scan.seen = PyMem_Calloc((size_t)scan.field_pool + scan.method_pool + 1, sizeof(uint32_t));
    if (!scan.seen) return PyErr_NoMemory();
    selected = PyList_New(0);
    definitions = PyList_New(0);
    matches = PyList_New(0);
    if (!selected || !definitions || !matches) goto finished_classes_select;
    for (i = 0; i < PyList_Size(directory); i++) {
        PyObject *row = PyList_GetItem(directory, i), *owner, *offset, *chosen;
        Py_ssize_t cls;
        if (++scan.generation == 0) {
            memset(scan.seen, 0, ((size_t)scan.field_pool + scan.method_pool + 1) * sizeof(uint32_t));
            scan.generation = 1;
        }
        if (!PyTuple_Check(row) || PyTuple_Size(row) != 2) {
            PyErr_SetString(PyExc_ValueError, "Invalid DEX selection directory row");
            goto finished_classes_select;
        }
        owner = PyTuple_GetItem(row, 0);
        offset = PyTuple_GetItem(row, 1);
        if (!PyUnicode_Check(owner)) {
            PyErr_SetString(PyExc_ValueError, "Invalid DEX class identity");
            goto finished_classes_select;
        }
        cls = PyLong_AsSsize_t(offset);
        if (PyErr_Occurred() || select_class_rows(&scan, cls, matches, definitions) < 0)
            goto finished_classes_select;
        if (!PyList_Size(matches)) continue;
        chosen = PyTuple_Pack(2, owner, matches);
        if (!chosen) goto finished_classes_select;
        if (PyList_Append(selected, chosen) < 0) { Py_DECREF(chosen); goto finished_classes_select; }
        Py_DECREF(chosen);
        Py_DECREF(matches);
        matches = PyList_New(0);
        if (!matches) goto finished_classes_select;
    }
    result = Py_BuildValue("OOKKKK", selected, definitions, scan.count, scan.instructions,
                           scan.dynamic, scan.without);
finished_classes_select:
    Py_XDECREF(selected);
    Py_XDECREF(definitions);
    Py_XDECREF(matches);
    PyMem_Free(scan.seen);
    return result;
}

static PyObject *select_methods(PyObject *self, PyObject *args) {
    PyObject *data_obj, *methods, *widths, *mask, *selected = NULL;
    char *raw, *width_raw, *mask_raw;
    const unsigned char *data;
    Py_ssize_t length, width_length, mask_length, method_offset, strings, protos, i;
    unsigned long long instructions = 0, dynamic = 0, without = 0;
    int version, fields, pool, access;
    (void)self;
    if (!PyArg_ParseTuple(args, "OOiOOiinnni", &data_obj, &methods, &version,
                         &widths, &mask, &fields, &pool, &method_offset, &strings,
                         &protos, &access)) return NULL;
    if (PyBytes_AsStringAndSize(data_obj, &raw, &length) < 0 ||
        PyBytes_AsStringAndSize(widths, &width_raw, &width_length) < 0 ||
        PyBytes_AsStringAndSize(mask, &mask_raw, &mask_length) < 0) return NULL;
    data = (const unsigned char *)raw;
    if (!PyList_Check(methods) || method_offset < 0 || method_offset > length ||
        strings < 0 || protos < 0 || width_length != 256 || mask_length != 65536 || pool < 0)
        goto invalid_select;
    selected = PyList_New(0);
    if (!selected) return NULL;
    for (i = 0; i < PyList_Size(methods); i++) {
        PyObject *method = PyList_GetItem(methods, i), *index_obj, *code_obj;
        Py_ssize_t index, code;
        int wanted;
        if (!PyTuple_Check(method) || PyTuple_Size(method) != 3) goto invalid_select;
        index_obj = PyTuple_GetItem(method, 0);
        code_obj = PyTuple_GetItem(method, 2);
        index = PyLong_AsSsize_t(index_obj);
        code = PyLong_AsSsize_t(code_obj);
        if (PyErr_Occurred()) goto failed_select;
        wanted = select_code(data, length, index, code, method_offset, strings, protos,
                             (unsigned char *)width_raw, (unsigned char *)mask_raw,
                             version, fields, pool, access, 1, &instructions, &dynamic, &without);
        if (wanted < 0) goto invalid_select;
        if (wanted && PyList_Append(selected, method) < 0) goto failed_select;
    }
    {
        PyObject *result = Py_BuildValue("OKKK", selected, instructions, dynamic, without);
        Py_DECREF(selected);
        return result;
    }
invalid_select:
    PyErr_SetString(PyExc_ValueError, "Invalid DEX method pool metadata");
failed_select:
    Py_XDECREF(selected);
    return NULL;
}

/* ASCII class descriptors are overwhelmingly common. Non-ASCII strings retain
 * the independent, strict modified-UTF8 decoder rather than a lossy shortcut. */
static PyObject *class_rows(const unsigned char *data, Py_ssize_t length,
                            Py_ssize_t class_offset, Py_ssize_t count,
                            Py_ssize_t type_offset, Py_ssize_t types,
                            Py_ssize_t string_offset, Py_ssize_t strings, int names_only, int checked) {
    PyObject *result = NULL, *seen = NULL, *deferred = NULL;
    Py_ssize_t i;
    if (class_offset < 0 || class_offset > length || count < 0 || count > (length-class_offset)/32 ||
        type_offset < 0 || type_offset > length || types < 0 || types > (length-type_offset)/4 ||
        string_offset < 0 || string_offset > length || strings < 0 || strings > (length-string_offset)/4)
        goto invalid_classes;
    result = PyList_New(0);
    if (!result) return NULL;
    if (checked) {
        seen = PySet_New(NULL);
        deferred = PyList_New(0);
        if (!seen || !deferred) goto failed_classes;
    }
    for (i = 0; i < count; i++) {
        Py_ssize_t offset = class_offset + i*32, position, end;
        uint32_t type = u32(data+offset), string, units;
        PyObject *name, *row;
        if (type >= (uint64_t)types) goto invalid_classes;
        string = u32(data+type_offset+type*4);
        if (string >= (uint64_t)strings) goto invalid_classes;
        position = u32(data+string_offset+string*4);
        if (position >= length || leb(data,length,&position,&units) < 0) goto invalid_classes;
        end = position;
        while (end < length && data[end] && data[end] < 128) end++;
        if (end == length) goto invalid_classes;
        if (data[end] == 0) {
            if ((uint64_t)(end-position) != units) goto invalid_classes;
            name = PyUnicode_DecodeASCII((const char *)data+position,end-position,"strict");
        } else { name = Py_None; Py_INCREF(name); }
        if (!name) goto failed_classes;
        if (checked && name != Py_None) {
            int duplicate = PySet_Contains(seen, name);
            if (duplicate < 0) { Py_DECREF(name); goto failed_classes; }
            if (duplicate) {
                Py_DECREF(name);
                PyErr_SetString(PyExc_ValueError, "Duplicate class definition");
                goto failed_classes;
            }
            if (PySet_Add(seen, name) < 0) { Py_DECREF(name); goto failed_classes; }
        } else if (checked) {
            PyObject *index = PyLong_FromSsize_t(i);
            int added;
            if (!index) { Py_DECREF(name); goto failed_classes; }
            added = PyList_Append(deferred, index);
            Py_DECREF(index);
            if (added < 0) { Py_DECREF(name); goto failed_classes; }
        }
        if (names_only) {
            if (name == Py_None) {
                Py_DECREF(name);
                row = PyLong_FromSsize_t(offset);
            } else row = name;
        } else {
            row = Py_BuildValue("On",name,offset);
            Py_DECREF(name);
        }
        if (!row) goto failed_classes;
        if (PyList_Append(result,row) < 0) { Py_DECREF(row); goto failed_classes; }
        Py_DECREF(row);
    }
    if (checked) {
        PyObject *wrapped = PyTuple_Pack(3, result, deferred, seen);
        Py_DECREF(result);
        Py_DECREF(deferred);
        Py_DECREF(seen);
        return wrapped;
    }
    return result;
invalid_classes:
    PyErr_SetString(PyExc_ValueError,"Invalid DEX class directory or string");
failed_classes:
    Py_XDECREF(result);
    Py_XDECREF(deferred);
    Py_XDECREF(seen);
    return NULL;
}

static PyObject *classes_impl(PyObject *args, int checked) {
    PyObject *data_obj;
    char *raw;
    Py_ssize_t length, class_offset, count, type_offset, types, string_offset, strings;
    if (!PyArg_ParseTuple(args, "Onnnnnn", &data_obj, &class_offset, &count,
                         &type_offset, &types, &string_offset, &strings)) return NULL;
    if (PyBytes_AsStringAndSize(data_obj, &raw, &length) < 0) return NULL;
    return class_rows((const unsigned char *)raw, length, class_offset, count,
                      type_offset, types, string_offset, strings, 0, checked);
}

static PyObject *classes(PyObject *self, PyObject *args) {
    (void)self;
    return classes_impl(args, 0);
}

static PyObject *checked_classes(PyObject *self, PyObject *args) {
    (void)self;
    return classes_impl(args, 1);
}

typedef struct {
    void *view;
    const unsigned char *data;
    size_t size;
} MappedRegion;

/* Map just one stored DEX window, not an entire APK's virtual address space.
 * Python owns the source handle. The view never escapes this synchronous call. */
static int map_region(Py_ssize_t handle, Py_ssize_t offset, Py_ssize_t length, MappedRegion *region) {
    uint64_t file_size, aligned, padding, granularity;
    if (handle < 0 || offset < 0 || length <= 0 || offset > PY_SSIZE_T_MAX-length)
        goto invalid_region;
#ifdef _WIN32
    {
        LARGE_INTEGER size;
        SYSTEM_INFO system;
        HANDLE mapping, file = (HANDLE)(intptr_t)handle;
        if (GetFileType(file) != FILE_TYPE_DISK || !GetFileSizeEx(file, &size)) {
            PyErr_SetFromWindowsErr(0); return -1;
        }
        file_size = (uint64_t)size.QuadPart;
        GetSystemInfo(&system);
        granularity = system.dwAllocationGranularity;
        if (!granularity || (uint64_t)offset > file_size || (uint64_t)length > file_size-offset)
            goto invalid_region;
        aligned = (uint64_t)offset / granularity * granularity;
        padding = (uint64_t)offset - aligned;
        if (padding > (uint64_t)PY_SSIZE_T_MAX-(uint64_t)length) goto invalid_region;
        region->size = (size_t)padding + (size_t)length;
        mapping = CreateFileMappingW(file, NULL, PAGE_READONLY, 0, 0, NULL);
        if (!mapping) { PyErr_SetFromWindowsErr(0); return -1; }
        region->view = MapViewOfFile(mapping, FILE_MAP_READ, (DWORD)(aligned >> 32),
                                    (DWORD)aligned, region->size);
        if (!region->view) {
            DWORD error = GetLastError();
            CloseHandle(mapping); PyErr_SetFromWindowsErr(error); return -1;
        }
        CloseHandle(mapping);
    }
#else
    {
        struct stat info;
        long page_size = sysconf(_SC_PAGESIZE);
        if (handle > INT_MAX || page_size <= 0) goto invalid_region;
        if (fstat((int)handle, &info) < 0) { PyErr_SetFromErrno(PyExc_OSError); return -1; }
        if (!S_ISREG(info.st_mode) || info.st_size < 0) goto invalid_region;
        file_size = (uint64_t)info.st_size;
        granularity = (uint64_t)page_size;
        if ((uint64_t)offset > file_size || (uint64_t)length > file_size-offset) goto invalid_region;
        aligned = (uint64_t)offset / granularity * granularity;
        padding = (uint64_t)offset - aligned;
        if (padding > (uint64_t)PY_SSIZE_T_MAX-(uint64_t)length) goto invalid_region;
        region->size = (size_t)padding + (size_t)length;
        region->view = mmap(NULL, region->size, PROT_READ, MAP_PRIVATE, (int)handle, (off_t)aligned);
        if (region->view == MAP_FAILED) { PyErr_SetFromErrno(PyExc_OSError); return -1; }
    }
#endif
    region->data = (const unsigned char *)region->view + (size_t)padding;
    return 0;
invalid_region:
    PyErr_SetString(PyExc_ValueError, "Invalid stored DEX mapping range or handle");
    return -1;
}

static void unmap_region(MappedRegion *region) {
#ifdef _WIN32
    UnmapViewOfFile(region->view);
#else
    munmap(region->view, region->size);
#endif
}

/* Validate every byte through short-lived mapping windows. Touching an entire
 * DEX mapping for CRC would unnecessarily keep its pages resident while class
 * identities are allocated. Owned chunks also cannot escape as dangling views. */
static int check_crc(Py_ssize_t handle, Py_ssize_t offset, Py_ssize_t length, uint32_t expected) {
    PyObject *module = PyImport_ImportModule("zlib"), *function = NULL;
    Py_ssize_t position;
    unsigned long crc = 0;
    int status = -1;
    if (!module) return -1;
    function = PyObject_GetAttrString(module, "crc32");
    if (!function) goto finished_crc;
    for (position = 0; position < length;) {
        Py_ssize_t size = length-position > 256*1024 ? 256*1024 : length-position;
        PyObject *block, *result;
        MappedRegion chunk;
        if (map_region(handle, offset+position, size, &chunk) < 0) goto finished_crc;
        block = PyBytes_FromStringAndSize((const char *)chunk.data, size);
        unmap_region(&chunk);
        if (!block) goto finished_crc;
        result = PyObject_CallFunction(function, "OI", block, (unsigned int)crc);
        Py_DECREF(block);
        if (!result) goto finished_crc;
        crc = PyLong_AsUnsignedLong(result);
        Py_DECREF(result);
        if (PyErr_Occurred()) goto finished_crc;
        position += size;
    }
    if (crc != expected) PyErr_SetString(PyExc_ValueError, "Stored DEX snapshot CRC mismatch");
    else status = 0;
finished_crc:
    Py_XDECREF(function);
    Py_DECREF(module);
    return status;
}

static PyObject *mapped_classes_impl(PyObject *args, int checked) {
    Py_ssize_t handle, offset, length;
    unsigned int crc;
    unsigned int position;
    const unsigned char *data;
    MappedRegion region;
    PyObject *result = NULL;
    if (!PyArg_ParseTuple(args, "nnnI", &handle, &offset, &length, &crc)) return NULL;
    if (map_region(handle, offset, length, &region) < 0) return NULL;
    data = region.data;
    if (length < 112 || memcmp(data, "dex\n", 4) || data[7] ||
        (memcmp(data+4,"035",3) && memcmp(data+4,"037",3) && memcmp(data+4,"038",3) &&
         memcmp(data+4,"039",3) && memcmp(data+4,"040",3)) ||
        u32(data+32) != (uint64_t)length || u32(data+36) != 112 || u32(data+40) != 0x12345678)
        goto invalid_mapped_classes;
    for (position = 56; position <= 96; position += 8) {
        uint32_t count = u32(data+position), start = u32(data+position+4);
        unsigned int width = position == 56 || position == 64 ? 4 :
            position == 72 ? 12 : position == 96 ? 32 : 8;
        if ((count && (start < 112 || start % 4 || (uint64_t)start+(uint64_t)count*width > (uint64_t)length)) ||
            (!count && start) || ((position == 80 || position == 88) && count > 65536))
            goto invalid_mapped_classes;
    }
    if (check_crc(handle, offset, length, crc) < 0) goto finished_mapped_classes;
    result = class_rows(data, length, u32(data+100), u32(data+96),
                         u32(data+68), u32(data+64), u32(data+60), u32(data+56), 1, checked);
    goto finished_mapped_classes;
invalid_mapped_classes:
    PyErr_SetString(PyExc_ValueError, "Invalid mapped DEX header or tables");
finished_mapped_classes:
    unmap_region(&region);
    return result;
}

static PyObject *mapped_classes(PyObject *self, PyObject *args) {
    (void)self;
    return mapped_classes_impl(args, 0);
}

static PyObject *mapped_checked_classes(PyObject *self, PyObject *args) {
    (void)self;
    return mapped_classes_impl(args, 1);
}

static unsigned char ascii_lower(unsigned char value) {
    return value >= 'A' && value <= 'Z' ? value + ('a' - 'A') : value;
}

/* Compare validated ASCII type names without allocating a Python string per
 * pool entry. Non-ASCII names must still pass the strict Python MUTF8 decoder. */
static PyObject *matching_types(PyObject *self, PyObject *args) {
    PyObject *data_obj, *query_obj, *matches = NULL, *deferred = NULL, *result = NULL;
    char *raw, *query;
    const unsigned char *data;
    Py_ssize_t length, query_length, type_offset, types, string_offset, strings, i;
    int fuzzy, sensitive;
    (void)self;
    if (!PyArg_ParseTuple(args, "OnnnnOpp", &data_obj, &type_offset, &types,
                         &string_offset, &strings, &query_obj, &fuzzy, &sensitive)) return NULL;
    if (PyBytes_AsStringAndSize(data_obj, &raw, &length) < 0 ||
        PyBytes_AsStringAndSize(query_obj, &query, &query_length) < 0) return NULL;
    data = (const unsigned char *)raw;
    if (type_offset < 0 || type_offset > length || types < 0 || types > (length-type_offset)/4 ||
        string_offset < 0 || string_offset > length || strings < 0 || strings > (length-string_offset)/4)
        goto invalid_types;
    for (i = 0; i < query_length; i++)
        if ((unsigned char)query[i] >= 128) goto invalid_types;
    matches = PyList_New(0);
    deferred = PyList_New(0);
    if (!matches || !deferred) goto failed_types;
    for (i = 0; i < types; i++) {
        uint32_t string = u32(data+type_offset+i*4), units;
        Py_ssize_t position, end, start, j, size;
        PyObject *index, *destination = NULL;
        if (string >= (uint64_t)strings) goto invalid_types;
        position = u32(data+string_offset+string*4);
        if (position >= length || leb(data,length,&position,&units) < 0) goto invalid_types;
        end = position;
        while (end < length && data[end] && data[end] < 128) end++;
        if (end == length) goto invalid_types;
        if (data[end]) destination = deferred;
        else {
            size = end-position;
            if ((uint64_t)size != units) goto invalid_types;
            if (query_length <= size && (fuzzy || query_length == size)) {
                for (start = 0; start <= (fuzzy ? size-query_length : 0); start++) {
                    for (j = 0; j < query_length; j++) {
                        unsigned char a = data[position+start+j], b = (unsigned char)query[j];
                        if ((sensitive ? a : ascii_lower(a)) != (sensitive ? b : ascii_lower(b))) break;
                    }
                    if (j == query_length) { destination = matches; break; }
                }
            }
        }
        if (destination) {
            index = PyLong_FromSsize_t(i);
            if (!index) goto failed_types;
            if (PyList_Append(destination,index) < 0) { Py_DECREF(index); goto failed_types; }
            Py_DECREF(index);
        }
    }
    result = PyTuple_Pack(2,matches,deferred);
    goto failed_types;
invalid_types:
    PyErr_SetString(PyExc_ValueError,"Invalid DEX type directory, query or string");
failed_types:
    Py_XDECREF(matches);
    Py_XDECREF(deferred);
    return result;
}

static PyObject *owner_members(PyObject *self, PyObject *args) {
    PyObject *data_obj, *mask_obj, *result;
    char *raw, *mask;
    Py_ssize_t length, mask_length, offset, count, types, i;
    (void)self;
    if (!PyArg_ParseTuple(args,"OnnnO",&data_obj,&offset,&count,&types,&mask_obj)) return NULL;
    if (PyBytes_AsStringAndSize(data_obj,&raw,&length) < 0 ||
        PyBytes_AsStringAndSize(mask_obj,&mask,&mask_length) < 0) return NULL;
    if (offset < 0 || offset > length || count < 0 || count > (length-offset)/8 ||
        types < 0 || mask_length != 65536) {
        PyErr_SetString(PyExc_ValueError,"Invalid DEX member directory or owner mask");
        return NULL;
    }
    result = PyList_New(0);
    if (!result) return NULL;
    for (i = 0; i < count; i++) {
        unsigned int owner = u16((const unsigned char *)raw+offset+i*8);
        PyObject *index;
        if (owner >= (uint64_t)types) {
            PyErr_SetString(PyExc_ValueError,"DEX member owner index out of bounds");
            Py_DECREF(result);
            return NULL;
        }
        if (!mask[owner]) continue;
        index = PyLong_FromSsize_t(i);
        if (!index || PyList_Append(result,index) < 0) {
            Py_XDECREF(index);
            Py_DECREF(result);
            return NULL;
        }
        Py_DECREF(index);
    }
    return result;
}

static PyMethodDef methods[] = {
    {"scan", scan, METH_VARARGS, "Scan checked instruction boundaries and selected operands."},
    {"members", members, METH_VARARGS, "Decode bounded DEX class member definitions."},
    {"select_methods", select_methods, METH_VARARGS, "Scan and count a bounded class method set."},
    {"select_class", select_class, METH_VARARGS, "Decode and select checked class data without unused rows."},
    {"select_classes", select_classes, METH_VARARGS, "Select a validated directory with the same checked class cursor."},
    {"classes", classes, METH_VARARGS, "Read checked ASCII class identities; defer modified UTF8."},
    {"checked_classes", checked_classes, METH_VARARGS, "Validate ASCII duplicates and return only deferred Unicode row indices."},
    {"mapped_classes", mapped_classes, METH_VARARGS, "Read CRC-checked names; defer only non-ASCII class offsets."},
    {"mapped_checked_classes", mapped_checked_classes, METH_VARARGS, "Read CRC-checked names and validate ASCII duplicates without a Python directory walk."},
    {"matching_types", matching_types, METH_VARARGS, "Match checked ASCII types; defer modified UTF8."},
    {"owner_members", owner_members, METH_VARARGS, "Select bounded member IDs by checked owner IDs."},
    {NULL, NULL, 0, NULL}
};
static struct PyModuleDef module = {
    PyModuleDef_HEAD_INIT, "_dexscan", NULL, -1, methods,
    NULL, NULL, NULL, NULL
};
PyMODINIT_FUNC PyInit__dexscan(void) { return PyModule_Create(&module); }
