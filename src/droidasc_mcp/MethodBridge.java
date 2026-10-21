import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import com.google.gson.GsonBuilder;
import com.android.tools.smali.dexlib2.DexFileFactory;
import com.android.tools.smali.dexlib2.ReferenceType;
import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedMethodImplementation;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedDexFile;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedMethod;
import com.android.tools.smali.dexlib2.dexbacked.raw.FieldIdItem;
import com.android.tools.smali.dexlib2.dexbacked.raw.MethodIdItem;
import com.android.tools.smali.dexlib2.dexbacked.instruction.DexBackedInstruction;
import com.android.tools.smali.dexlib2.iface.*;
import com.android.tools.smali.dexlib2.iface.instruction.*;
import com.android.tools.smali.dexlib2.iface.instruction.formats.UnknownInstruction;
import com.android.tools.smali.dexlib2.iface.instruction.formats.ArrayPayload;
import com.android.tools.smali.dexlib2.iface.reference.*;
import com.android.tools.smali.baksmali.BaksmaliOptions;
import com.android.tools.smali.baksmali.Adaptors.ClassDefinition;
import com.android.tools.smali.baksmali.Adaptors.MethodDefinition;
import com.android.tools.smali.baksmali.formatter.BaksmaliWriter;
import jadx.api.*;

/** Isolated optional backend. Identity comes from DEX, never decompiled Java text. */
public class MethodBridge {
    static String descriptor(MethodReference method) {
        StringBuilder result = new StringBuilder(method.getDefiningClass())
            .append("->");
        return result.append(localDescriptor(method)).toString();
    }

    static String localDescriptor(MethodReference method) {
        StringBuilder result = new StringBuilder(method.getName()).append('(');
        for (CharSequence type : method.getParameterTypes()) result.append(type);
        return result.append(')').append(method.getReturnType()).toString();
    }

    static String descriptor(FieldReference field) {
        return field.getDefiningClass() + "->" + field.getName() + ":" + field.getType();
    }

    static final class MethodKey implements Comparable<MethodKey> {
        final MemberNames names;
        final int index;
        final String prefix;
        final String prototype;
        String descriptor;

        MethodKey(Method method, MemberNames names) {
            this.names = names;
            index = ((DexBackedMethod) method).methodIndex;
            // Include '(' so prefix names such as a$ and a preserve descriptor order.
            prefix = names.methodName(index) + '(';
            // Still validate every definition's prototype, even for unreferenced methods.
            prototype = names.methodProto(index);
        }

        String text() {
            if (descriptor == null) descriptor = names.methodName(index) + prototype;
            return descriptor;
        }

        public int compareTo(MethodKey other) {
            int order = prefix.compareTo(other.prefix);
            return order == 0 ? text().compareTo(other.text()) : order;
        }
    }

    /** Query-local DEX pools: decode repeated names/types/prototypes once, not per member. */
    static final class MemberNames {
        final DexBackedDexFile dex;
        final String[] strings, types, protos;

        MemberNames(DexBackedDexFile dex) {
            this.dex = dex;
            strings = new String[dex.getStringSection().size()];
            types = new String[dex.getTypeSection().size()];
            protos = new String[dex.getProtoSection().size()];
        }

        String string(int index) {
            if (strings[index] == null) strings[index] = dex.getStringSection().get(index);
            return strings[index];
        }

        String type(int index) {
            if (types[index] == null) types[index] = dex.getTypeSection().get(index);
            return types[index];
        }

        String proto(int index) {
            if (protos[index] == null) {
                var reference = dex.getProtoSection().get(index);
                StringBuilder value = new StringBuilder("(");
                for (CharSequence parameter : reference.getParameterTypes()) value.append(parameter);
                protos[index] = value.append(')').append(reference.getReturnType()).toString();
            }
            return protos[index];
        }

        String methodName(int index) {
            int position = dex.getMethodSection().getOffset(index);
            return string(dex.getBuffer().readSmallUint(position + MethodIdItem.NAME_OFFSET));
        }

        String methodProto(int index) {
            int position = dex.getMethodSection().getOffset(index);
            return proto(dex.getBuffer().readUshort(position + MethodIdItem.PROTO_OFFSET));
        }

        String localMethod(int index) {
            return methodName(index) + methodProto(index);
        }

        String member(int index, boolean field) {
            int position = field ? dex.getFieldSection().getOffset(index)
                : dex.getMethodSection().getOffset(index);
            var buffer = dex.getBuffer();
            String owner = type(buffer.readUshort(position));
            if (!field) return owner + "->" + localMethod(index);
            return owner + "->" + string(buffer.readSmallUint(position + FieldIdItem.NAME_OFFSET))
                + ":" + type(buffer.readUshort(position + FieldIdItem.TYPE_OFFSET));
        }
    }

    static String definition(String member, boolean field, Map<String, ClassDef> owners,
            Map<String, String> origins) {
        String owner = member.substring(0, member.indexOf("->"));
        ClassDef cls = owners.get(owner);
        if (cls == null) return null;
        boolean found = false;
        if (field) {
            for (Field candidate : cls.getFields()) {
                if (descriptor(candidate).equals(member)) {
                    if (found) throw new IllegalArgumentException("Duplicate field definition");
                    found = true;
                }
            }
        } else {
            for (Method candidate : cls.getMethods()) {
                if (descriptor(candidate).equals(member)) {
                    if (found) throw new IllegalArgumentException("Duplicate method definition");
                    found = true;
                }
            }
        }
        return found ? origins.get(owner) : null;
    }

    /** Walk exact boundaries using the pinned decoder's version-specific format table.
     * Only payloads and requested operands need allocated instruction objects. */
    static final class InstructionCursor {
        final DexBackedDexFile dex;
        final Opcode[] opcodes;
        final int start, end;
        int next, position, units;
        long address;
        Opcode opcode;
        Instruction decoded;

        static Opcode[] table(Opcodes version) {
            Opcode[] table = new Opcode[256];
            for (int i = 0; i < table.length; i++) table[i] = version.getOpcodeByValue(i);
            return table;
        }

        InstructionCursor(MethodImplementation implementation) {
            this(implementation, table(((DexBackedMethodImplementation) implementation).dexFile.getOpcodes()));
        }

        InstructionCursor(MethodImplementation implementation, Opcode[] table) {
            var backed = (DexBackedMethodImplementation) implementation;
            dex = backed.dexFile;
            opcodes = table;
            int size = backed.getInstructionsSize();
            start = size == 0 ? 0 : ((DexBackedInstruction)
                backed.getInstructions().iterator().next()).instructionStart;
            long stop = start + 2L * size;
            var buffer = dex.getDataBuffer();
            if (size < 0 || start < 0 || stop > buffer.getBuf().length - buffer.getBaseOffset())
                throw new IllegalArgumentException("Invalid DEX instruction range");
            end = (int) stop;
            next = start;
        }

        boolean advance() {
            if (next == end) return false;
            position = next;
            address = (position - start) / 2L;
            decoded = null;
            var buffer = dex.getDataBuffer();
            int value = buffer.readUbyte(position);
            opcode = value == 0 ? dex.getOpcodes().getOpcodeByValue(buffer.readUshort(position))
                : opcodes[value];
            if (opcode == null || opcode.odexOnly())
                throw new IllegalArgumentException("Unknown or optimized DEX instruction");
            long count = opcode.format.size / 2;
            if (opcode.format.isPayloadFormat) {
                int header = opcode.format == com.android.tools.smali.dexlib2.Format.ArrayPayload ? 8 : 4;
                if ((long) position + header > end)
                    throw new IllegalArgumentException("Truncated DEX payload header");
                var payload = instruction();
                if (payload instanceof ArrayPayload array) {
                    int width = array.getElementWidth();
                    if (width != 1 && width != 2 && width != 4 && width != 8)
                        throw new IllegalArgumentException("Invalid DEX array element width");
                    count = 4 + ((long) width * array.getArrayElements().size() + 1) / 2;
                } else if (payload instanceof SwitchPayload switches) {
                    count = opcode.format == com.android.tools.smali.dexlib2.Format.PackedSwitchPayload
                        ? 4L + 2L * switches.getSwitchElements().size()
                        : 2L + 4L * switches.getSwitchElements().size();
                } else throw new IllegalArgumentException("Unknown DEX payload format");
            }
            if (count <= 0 || (long) position + count * 2 > end)
                throw new IllegalArgumentException("Truncated or oversized DEX instruction");
            units = (int) count;
            next = position + units * 2;
            return true;
        }

        Instruction instruction() {
            if (decoded == null)
                decoded = DexBackedInstruction.readFrom(dex, dex.getDataBuffer().readerAt(position));
            if (decoded instanceof UnknownInstruction)
                throw new IllegalArgumentException("Unknown DEX instruction");
            return decoded;
        }
    }

    static boolean matches(InstructionCursor cursor, String requested, byte[] memo, MemberNames names,
            boolean fields) {
        // These validated standard member formats all store the ID at code unit one.
        int index = cursor.dex.getDataBuffer().readUshort(cursor.position + 2);
        if (memo[index] != 0) return memo[index] == 1;
        String value = names.member(index, fields);
        boolean matched = value.equals(requested);
        memo[index] = (byte) (matched ? 1 : 2);
        return matched;
    }

    static Map<String, Object> run(String[] args) throws Exception {
        File input = new File(args[0]);
        String entry = args[1], className = args[2], operation = args[3];
        String requested = args[4], format = args[5];
        int offset = Integer.parseInt(args[6]), limit = Integer.parseInt(args[7]);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("backend", "jadx-dexlib2");
        result.put("backend_version", JadxDecompiler.getVersion());
        if (!"1.5.5".equals(JadxDecompiler.getVersion())) {
            result.put("status", "error");
            result.put("code", "unsupported_backend_version");
            return result;
        }
        if (operation.equals("find_method_refs") || operation.equals("get_method_calls")
                || operation.equals("find_field_refs")) {
            return references(input, requested, operation, args[8], offset, limit, result);
        }
        ClassDef owner = null;
        var dex = DexFileFactory.loadDexEntry(input, entry, true, null).getDexFile();
        for (ClassDef cls : dex.getClasses()) {
            if (className.equals(cls.getType())) { owner = cls; break; }
        }
        if (owner == null) throw new IllegalArgumentException("Class missing from owning DEX");
        TreeMap<String, Method> methods = new TreeMap<>();
        for (Method method : owner.getMethods()) {
            if (methods.put(descriptor(method), method) != null)
                throw new IllegalArgumentException("Duplicate method definition");
        }
        result.put("status", "ok");
        if (operation.equals("list_methods")) {
            List<Map<String, Object>> items = new ArrayList<>();
            for (var item : methods.entrySet()) {
                Method method = item.getValue();
                items.add(Map.of("descriptor", item.getKey(), "name", method.getName(),
                    "parameter_types", method.getParameterTypes(), "return_type", method.getReturnType(),
                    "access_flags", method.getAccessFlags(), "has_code", method.getImplementation() != null));
            }
            result.put("total", items.size());
            result.put("items", items.subList(Math.min(offset, items.size()),
                (int) Math.min((long) offset + limit, items.size())));
            return result;
        }
        Method target = methods.get(requested);
        result.put("method_descriptor", requested);
        if (target == null) {
            result.put("status", "error");
            result.put("code", "method_not_found");
            return result;
        }
        String code = "", reason = "", mode = format;
        if (!format.equals("smali")) {
            JadxArgs options = new JadxArgs();
            options.setInputFile(input);
            options.setThreadsCount(1);
            options.setSkipResources(true);
            options.setInlineMethods(false);
            options.setInlineAnonymousClasses(false);
            options.setMoveInnerClasses(false);
            options.setDeobfuscationOn(false);
            options.setSkipFilesSave(true);
            try (JadxDecompiler jadx = new JadxDecompiler(options)) {
                jadx.load();
                JavaClass cls = jadx.searchJavaClassByOrigFullName(
                    className.substring(1, className.length() - 1).replace('/', '.'));
                if (cls != null) {
                    cls.decompile();
                    JavaMethod method = cls.searchMethodByShortId(requested.substring(className.length() + 2));
                    if (method != null) code = method.getCodeStr();
                }
                result.put("java_error_count", jadx.getErrorsCount());
                result.put("java_warning_count", jadx.getWarnsCount());
                if (jadx.getErrorsCount() > 0) { code = ""; reason = "java_decompilation_error"; }
                else if (code == null || code.isBlank()) { code = ""; reason = "java_method_not_emitted"; }
                else mode = "java";
            } catch (Exception error) {
                code = "";
                reason = "java_backend_error:" + error.getClass().getSimpleName();
            }
            if (code.isEmpty() && format.equals("java")) {
                result.put("status", "error");
                result.put("code", "java_unavailable");
                result.put("reason", reason);
                return result;
            }
        }
        if (code.isEmpty()) {
            StringWriter output = new StringWriter();
            BaksmaliWriter writer = new BaksmaliWriter(output);
            ClassDefinition cls = new ClassDefinition(new BaksmaliOptions(), owner);
            if (target.getImplementation() == null) MethodDefinition.writeEmptyMethodTo(writer, target, cls);
            else new MethodDefinition(cls, target, target.getImplementation()).writeTo(writer);
            writer.flush();
            code = output.toString();
            mode = "smali";
        }
        List<String> lines = code.lines().toList();
        result.put("format", mode);
        result.put("fell_back", format.equals("auto") && mode.equals("smali"));
        result.put("fallback_reason", reason);
        result.put("total", lines.size());
        result.put("source", String.join("\n", lines.subList(Math.min(offset, lines.size()),
            (int) Math.min((long) offset + limit, lines.size()))));
        return result;
    }

    static Map<String, Object> references(File input, String requested, String operation, String access,
            int offset, int limit, Map<String, Object> result) throws Exception {
        // Null selects opcodes from each DEX header, including modern invoke instructions.
        var container = DexFileFactory.loadDexContainer(input, null);
        var entries = new ArrayList<>(container.getDexEntryNames());
        Collections.sort(entries);
        boolean fields = operation.equals("find_field_refs");
        // Resolve only queried operands; instruction scanning stays independent and complete.
        Map<String, ClassDef> owners = new HashMap<>();
        Map<String, String> origins = new HashMap<>();
        Map<String, TreeMap<String, ClassDef>> orderedClasses = new HashMap<>();
        for (String entry : entries) {
            TreeMap<String, ClassDef> classes = new TreeMap<>();
            for (ClassDef cls : container.getEntry(entry).getDexFile().getClasses()) {
                String type = cls.getType();
                if (owners.put(type, cls) != null)
                    throw new IllegalArgumentException("Duplicate class definition");
                origins.put(type, entry);
                classes.put(type, cls);
            }
            orderedClasses.put(entry, classes);
        }
        Map<String, String> definitions = new HashMap<>();
        definitions.put(requested, definition(requested, fields, owners, origins));
        boolean incoming = !operation.equals("get_method_calls");
        result.put(fields ? "field_descriptor" : "method_descriptor", requested);
        if (fields) result.put("field_access", access);
        result.put("status", "ok");
        if (!incoming && definitions.get(requested) == null) {
            result.put("status", "error");
            result.put("code", "method_not_found");
            return result;
        }
        long total = 0, scannedMethods = 0, scannedInstructions = 0, withoutCode = 0;
        long dynamicSites = 0, unresolvedMatches = 0;
        List<Map<String, Object>> items = new ArrayList<>();
        List<Map<String, Object>> unresolved = new ArrayList<>();
        for (String entry : entries) {
            // Member IDs are local to each DEX and to this one method/field query.
            byte[] memo = incoming ? new byte[65536] : null;
            var dex = container.getEntry(entry).getDexFile();
            var names = new MemberNames(dex);
            Opcode[] opcodes = InstructionCursor.table(dex.getOpcodes());
            for (var owner : orderedClasses.get(entry).entrySet()) {
                ClassDef cls = owner.getValue();
                String classType = owner.getKey();
                if (!incoming && !requested.startsWith(classType + "->")) continue;
                TreeMap<MethodKey, Method> methods = new TreeMap<>();
                for (Method method : cls.getMethods()) {
                    if (methods.put(new MethodKey(method, names), method) != null)
                        throw new IllegalArgumentException("Duplicate method definition");
                }
                for (var member : methods.entrySet()) {
                    if (!incoming && !member.getKey().text().equals(requested.substring(requested.indexOf("->") + 2)))
                        continue;
                    String caller = null;
                    scannedMethods++;
                    MethodImplementation implementation = member.getValue().getImplementation();
                    if (implementation == null) { withoutCode++; continue; }
                    var cursor = new InstructionCursor(implementation, opcodes);
                    while (cursor.advance()) {
                        long address = cursor.address;
                        scannedInstructions++;
                        String opcode = cursor.opcode.name;
                        int referenceType = cursor.opcode.referenceType;
                        if (referenceType == ReferenceType.METHOD || referenceType == ReferenceType.FIELD
                                || referenceType == ReferenceType.CALL_SITE
                                || referenceType == ReferenceType.METHOD_HANDLE) {
                            String callee = null, fieldAccess = null;
                            if (!fields && referenceType == ReferenceType.METHOD) {
                                callee = incoming
                                    ? (matches(cursor, requested, memo, names, false) ? requested : null)
                                    : descriptor((MethodReference) ((ReferenceInstruction)
                                        cursor.instruction()).getReference());
                            } else if (fields && referenceType == ReferenceType.FIELD) {
                                callee = matches(cursor, requested, memo, names, true) ? requested : null;
                                if (callee != null) {
                                    if (opcode.startsWith("iget") || opcode.startsWith("sget"))
                                        fieldAccess = "read";
                                    else if (opcode.startsWith("iput") || opcode.startsWith("sput"))
                                        fieldAccess = "write";
                                    else throw new IllegalArgumentException("Unknown field access opcode");
                                }
                            }
                            if (callee != null) {
                                if ((!incoming || callee.equals(requested))
                                        && (!fields || access.equals("all") || access.equals(fieldAccess))) {
                                    if (!definitions.containsKey(callee))
                                        definitions.put(callee, definition(callee, fields, owners, origins));
                                    String targetEntry = definitions.get(callee);
                                    if (targetEntry == null) unresolvedMatches++;
                                    if (total >= offset && total - offset < limit) {
                                        if (caller == null) caller = classType + "->" + member.getKey().text();
                                        Map<String, Object> row = new LinkedHashMap<>();
                                        row.put("caller", caller);
                                        row.put(fields ? "field_descriptor" : "callee", callee);
                                        if (fields) {
                                            row.put("access", fieldAccess);
                                            row.put("storage", opcode.startsWith("s") ? "static" : "instance");
                                        }
                                        row.put("dex_entry", entry);
                                        row.put("instruction_offset", address);
                                        row.put("offset_unit", "code_units_from_method_start");
                                        row.put("opcode", opcode);
                                        row.put("target_resolution", targetEntry == null
                                            ? "not_defined_in_input" : "defined_in_input");
                                        row.put("target_dex_entry", targetEntry);
                                        if (cursor.instruction() instanceof DualReferenceInstruction dual
                                                && dual.getReference2() instanceof MethodProtoReference proto) {
                                            StringBuilder prototype = new StringBuilder("(");
                                            for (CharSequence type : proto.getParameterTypes()) prototype.append(type);
                                            row.put("call_site_prototype", prototype.append(')')
                                                .append(proto.getReturnType()).toString());
                                        }
                                        items.add(row);
                                    }
                                    total++;
                                }
                            }
                            if (referenceType == ReferenceType.CALL_SITE
                                    || referenceType == ReferenceType.METHOD_HANDLE
                                    || cursor.opcode == Opcode.INVOKE_POLYMORPHIC
                                    || cursor.opcode == Opcode.INVOKE_POLYMORPHIC_RANGE) {
                                dynamicSites++;
                                if (caller == null) caller = classType + "->" + member.getKey().text();
                                if (unresolved.size() < 20) unresolved.add(Map.of(
                                    "caller", caller, "dex_entry", entry,
                                    "instruction_offset", address, "opcode", opcode,
                                    "reason", "dynamic_target_not_resolved"));
                            }
                        }
                    }
                }
            }
        }
        result.put("backend", "dexlib2-instructions");
        result.put("total", total);
        result.put("items", items);
        result.put("reference_semantics", fields ? "declared_field_operand" : "declared_method_operand");
        result.put("scan_scope", incoming ? "supplied_dex_methods" : "selected_method");
        result.put("scanned_methods", scannedMethods);
        result.put("scanned_instructions", scannedInstructions);
        result.put("methods_without_code", withoutCode);
        result.put("scan_errors", 0);
        result.put("unresolved_matches", unresolvedMatches);
        result.put("dynamic_sites", dynamicSites);
        result.put("unresolved_sites", unresolved);
        result.put("unresolved_sites_truncated", dynamicSites > unresolved.size());
        result.put("instruction_scan_complete", true);
        result.put("runtime_target_resolution", "not_performed");
        result.put("limitations", fields
            ? List.of("inherited_field_resolution", "reflection", "jni", "runtime_loaded_code",
                "encoded_initial_values", "method_handle_targets")
            : List.of("virtual_dispatch", "reflection", "jni", "runtime_loaded_code"));
        return result;
    }

    public static void main(String[] args) throws Exception {
        PrintStream output = System.out;
        System.setOut(System.err);
        Map<String, Object> result = run(args);
        output.write(new GsonBuilder().serializeNulls().create().toJson(result).getBytes(StandardCharsets.UTF_8));
    }
}
