#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdint.h>
#include <string.h>

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
        Py_ssize_t index, code, position, end;
        int wanted = 0;
        if (!PyTuple_Check(method) || PyTuple_Size(method) != 3) goto invalid_select;
        index_obj = PyTuple_GetItem(method, 0);
        code_obj = PyTuple_GetItem(method, 2);
        index = PyLong_AsSsize_t(index_obj);
        code = PyLong_AsSsize_t(code_obj);
        if (PyErr_Occurred()) goto failed_select;
        if (index < 0 || index >= (length - method_offset) / 8) goto invalid_select;
        if (u32((unsigned char *)raw + method_offset + index * 8 + 4) >= (uint64_t)strings ||
            u16((unsigned char *)raw + method_offset + index * 8 + 2) >= (uint64_t)protos)
            goto invalid_select;
        if (!code) { without++; continue; }
        if (code < 0 || code % 4 || code > length || length - code < 16) goto invalid_select;
        position = code + 16;
        if ((uint64_t)u32(data + code + 12) * 2 > (uint64_t)(length - position))
            goto invalid_select;
        end = position + (Py_ssize_t)u32(data + code + 12) * 2;
        while (position < end) {
            unsigned int op;
            uint64_t bytes;
            int special;
            if (decode(data, (unsigned char *)width_raw, (unsigned char *)mask_raw,
                       position, end, version, fields, 1, pool, &op, &bytes, &special) < 0)
                goto invalid_select;
            instructions++;
            if (op >= 0xfa && op <= 0xfe) { dynamic++; wanted = 1; }
            if (special && (fields ? (op >= 0x52 && op <= 0x6d) :
                ((op >= 0x6e && op <= 0x72) || (op >= 0x74 && op <= 0x78) || op == 0xfa || op == 0xfb))) {
                int read = (op >= 0x52 && op <= 0x58) || (op >= 0x60 && op <= 0x66);
                if (!fields || !access || access == (read ? 1 : 2)) wanted = 1;
            }
            position += (Py_ssize_t)bytes;
        }
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
static PyObject *classes(PyObject *self, PyObject *args) {
    PyObject *data_obj, *result = NULL;
    char *raw;
    const unsigned char *data;
    Py_ssize_t length, class_offset, count, type_offset, types, string_offset, strings, i;
    (void)self;
    if (!PyArg_ParseTuple(args, "Onnnnnn", &data_obj, &class_offset, &count,
                         &type_offset, &types, &string_offset, &strings)) return NULL;
    if (PyBytes_AsStringAndSize(data_obj, &raw, &length) < 0) return NULL;
    data = (const unsigned char *)raw;
    if (class_offset < 0 || class_offset > length || count < 0 || count > (length-class_offset)/32 ||
        type_offset < 0 || type_offset > length || types < 0 || types > (length-type_offset)/4 ||
        string_offset < 0 || string_offset > length || strings < 0 || strings > (length-string_offset)/4)
        goto invalid_classes;
    result = PyList_New(0);
    if (!result) return NULL;
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
        row = Py_BuildValue("On",name,offset);
        Py_DECREF(name);
        if (!row) goto failed_classes;
        if (PyList_Append(result,row) < 0) { Py_DECREF(row); goto failed_classes; }
        Py_DECREF(row);
    }
    return result;
invalid_classes:
    PyErr_SetString(PyExc_ValueError,"Invalid DEX class directory or string");
failed_classes:
    Py_XDECREF(result);
    return NULL;
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
    {"classes", classes, METH_VARARGS, "Read checked ASCII class identities; defer modified UTF8."},
    {"matching_types", matching_types, METH_VARARGS, "Match checked ASCII types; defer modified UTF8."},
    {"owner_members", owner_members, METH_VARARGS, "Select bounded member IDs by checked owner IDs."},
    {NULL, NULL, 0, NULL}
};
static struct PyModuleDef module = {
    PyModuleDef_HEAD_INIT, "_dexscan", NULL, -1, methods,
    NULL, NULL, NULL, NULL
};
PyMODINIT_FUNC PyInit__dexscan(void) { return PyModule_Create(&module); }
