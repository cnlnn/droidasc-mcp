import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import com.google.gson.GsonBuilder;
import com.android.tools.smali.dexlib2.DexFileFactory;
import com.android.tools.smali.dexlib2.iface.*;
import com.android.tools.smali.dexlib2.iface.instruction.*;
import com.android.tools.smali.dexlib2.iface.instruction.formats.UnknownInstruction;
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
            .append("->").append(method.getName()).append('(');
        for (CharSequence type : method.getParameterTypes()) result.append(type);
        return result.append(')').append(method.getReturnType()).toString();
    }

    static String descriptor(FieldReference field) {
        return field.getDefiningClass() + "->" + field.getName() + ":" + field.getType();
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
        // Index definitions only. Instructions remain streamed and output is paged while scanning.
        Map<String, String> definitions = new HashMap<>();
        for (String entry : entries) {
            for (ClassDef cls : container.getEntry(entry).getDexFile().getClasses()) {
                if (fields) {
                    for (Field field : cls.getFields()) {
                        if (definitions.put(descriptor(field), entry) != null)
                            throw new IllegalArgumentException("Duplicate field definition");
                    }
                } else {
                    for (Method method : cls.getMethods()) {
                        if (definitions.put(descriptor(method), entry) != null)
                            throw new IllegalArgumentException("Duplicate method definition");
                    }
                }
            }
        }
        boolean incoming = !operation.equals("get_method_calls");
        result.put(fields ? "field_descriptor" : "method_descriptor", requested);
        if (fields) result.put("field_access", access);
        result.put("status", "ok");
        if (!incoming && !definitions.containsKey(requested)) {
            result.put("status", "error");
            result.put("code", "method_not_found");
            return result;
        }
        long total = 0, scannedMethods = 0, scannedInstructions = 0, withoutCode = 0;
        long dynamicSites = 0, unresolvedMatches = 0;
        List<Map<String, Object>> items = new ArrayList<>();
        List<Map<String, Object>> unresolved = new ArrayList<>();
        for (String entry : entries) {
            TreeMap<String, ClassDef> classes = new TreeMap<>();
            for (ClassDef cls : container.getEntry(entry).getDexFile().getClasses())
                classes.put(cls.getType(), cls);
            for (ClassDef cls : classes.values()) {
                TreeMap<String, Method> methods = new TreeMap<>();
                for (Method method : cls.getMethods()) methods.put(descriptor(method), method);
                for (var member : methods.entrySet()) {
                    String caller = member.getKey();
                    if (!incoming && !caller.equals(requested)) continue;
                    scannedMethods++;
                    MethodImplementation implementation = member.getValue().getImplementation();
                    if (implementation == null) { withoutCode++; continue; }
                    long address = 0;
                    for (Instruction instruction : implementation.getInstructions()) {
                        if (instruction instanceof UnknownInstruction || instruction.getOpcode().odexOnly())
                            throw new IllegalArgumentException("Unknown or optimized DEX instruction");
                        scannedInstructions++;
                        String opcode = instruction.getOpcode().name;
                        if (instruction instanceof ReferenceInstruction referenced) {
                            Reference reference = referenced.getReference();
                            String callee = null, fieldAccess = null;
                            if (!fields && reference instanceof MethodReference method) {
                                callee = descriptor(method);
                            } else if (fields && reference instanceof FieldReference field) {
                                callee = descriptor(field);
                                if (opcode.startsWith("iget") || opcode.startsWith("sget"))
                                    fieldAccess = "read";
                                else if (opcode.startsWith("iput") || opcode.startsWith("sput"))
                                    fieldAccess = "write";
                                else throw new IllegalArgumentException("Unknown field access opcode");
                            }
                            if (callee != null) {
                                if ((!incoming || callee.equals(requested))
                                        && (!fields || access.equals("all") || access.equals(fieldAccess))) {
                                    String targetEntry = definitions.get(callee);
                                    if (targetEntry == null) unresolvedMatches++;
                                    if (total >= offset && total - offset < limit) {
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
                                        if (instruction instanceof DualReferenceInstruction dual
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
                            if (reference instanceof CallSiteReference
                                    || reference instanceof MethodHandleReference
                                    || opcode.startsWith("invoke-polymorphic")) {
                                dynamicSites++;
                                if (unresolved.size() < 20) unresolved.add(Map.of(
                                    "caller", caller, "dex_entry", entry,
                                    "instruction_offset", address, "opcode", opcode,
                                    "reason", "dynamic_target_not_resolved"));
                            }
                        }
                        address += instruction.getCodeUnits();
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
