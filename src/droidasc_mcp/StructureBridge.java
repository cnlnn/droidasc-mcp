import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import com.google.gson.GsonBuilder;
import com.android.tools.smali.dexlib2.DexFileFactory;
import com.android.tools.smali.dexlib2.iface.*;
import com.android.tools.smali.dexlib2.iface.instruction.*;
import com.android.tools.smali.dexlib2.iface.reference.StringReference;
import com.android.tools.smali.baksmali.BaksmaliOptions;
import com.android.tools.smali.baksmali.Adaptors.ClassDefinition;
import com.android.tools.smali.baksmali.Adaptors.MethodDefinition;
import com.android.tools.smali.baksmali.Adaptors.RegisterFormatter;
import com.android.tools.smali.dexlib2.util.MethodUtil;
import com.android.tools.smali.baksmali.Adaptors.Format.InstructionMethodItemFactory;
import com.android.tools.smali.baksmali.formatter.BaksmaliWriter;
import jadx.api.JadxDecompiler;

/** Bounded structural views and decoded-instruction discovery, without decompilation. */
public class StructureBridge {
    static String descriptor(Method method) {
        StringBuilder value = new StringBuilder(method.getDefiningClass())
            .append("->").append(method.getName()).append('(');
        for (CharSequence type : method.getParameterTypes()) value.append(type);
        return value.append(')').append(method.getReturnType()).toString();
    }

    static class Page {
        long total, offset;
        int limit;
        List<Map<String, Object>> items = new ArrayList<>();
        Page(long offset, int limit) { this.offset = offset; this.limit = limit; }
        void add(Map<String, Object> row) {
            if (total >= offset && total - offset < limit) items.add(row);
            total++;
        }
    }

    static Map<String, Object> run(String[] args) throws Exception {
        if (!"1.5.5".equals(JadxDecompiler.getVersion()))
            return Map.of("status", "error", "code", "unsupported_backend_version");
        String operation = args[1], owner = args[2], needle = args[3], requested = args[7];
        boolean sensitive = Boolean.parseBoolean(args[6]);
        if (!sensitive) needle = needle.toLowerCase(Locale.ROOT);
        Page page = new Page(Long.parseLong(args[4]), Integer.parseInt(args[5]));
        var container = DexFileFactory.loadDexContainer(new File(args[0]), null);
        TreeMap<String, ClassDef> classes = new TreeMap<>();
        Map<String, String> origins = new HashMap<>();
        var entries = new ArrayList<>(container.getDexEntryNames());
        Collections.sort(entries);
        for (String entry : entries) {
            for (ClassDef cls : container.getEntry(entry).getDexFile().getClasses()) {
                if (classes.put(cls.getType(), cls) != null)
                    throw new IllegalArgumentException("Duplicate class definition");
                origins.put(cls.getType(), entry);
            }
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("status", "ok");
        result.put("backend", "dexlib2-structure");
        result.put("backend_version", JadxDecompiler.getVersion());
        result.put("runtime_target_resolution", "not_performed");
        result.put("scope", "supplied_dex_definitions_only");
        if (!owner.isEmpty() && !classes.containsKey(owner))
            return Map.of("status", "error", "code", "class_not_found");
        if (operation.equals("get_class_outline")) {
            ClassDef cls = classes.get(owner);
            result.put("class_name", owner);
            result.put("dex_entry", origins.get(owner));
            result.put("access_flags", cls.getAccessFlags());
            result.put("superclass", cls.getSuperclass());
            // Interfaces and members share one page, so pathological classes stay bounded.
            for (String type : new TreeSet<>(cls.getInterfaces()))
                page.add(Map.of("kind", "interface", "type_descriptor", type));
            TreeMap<String, Field> fields = new TreeMap<>();
            for (Field field : cls.getFields()) {
                String id = owner + "->" + field.getName() + ":" + field.getType();
                if (fields.put(id, field) != null) throw new IllegalArgumentException("Duplicate field");
            }
            for (var row : fields.entrySet()) {
                Field field = row.getValue();
                page.add(Map.of("kind", "field", "descriptor", row.getKey(), "name", field.getName(),
                    "type_descriptor", field.getType(), "access_flags", field.getAccessFlags(),
                    "storage", (field.getAccessFlags() & 8) != 0 ? "static" : "instance"));
            }
            TreeMap<String, Method> methods = new TreeMap<>();
            for (Method method : cls.getMethods()) {
                if (methods.put(descriptor(method), method) != null)
                    throw new IllegalArgumentException("Duplicate method");
            }
            for (var row : methods.entrySet()) {
                Method method = row.getValue();
                page.add(Map.of("kind", "method", "descriptor", row.getKey(), "name", method.getName(),
                    "access_flags", method.getAccessFlags(), "parameter_types", method.getParameterTypes(),
                    "return_type", method.getReturnType(), "has_code", method.getImplementation() != null,
                    "dispatch_kind", ((method.getAccessFlags() & (8 | 2)) != 0
                        || method.getName().equals("<init>")) ? "direct" : "virtual"));
            }
            result.put("field_count", fields.size());
            result.put("method_count", methods.size());
        } else if (operation.equals("get_class_hierarchy")) {
            ClassDef cls = classes.get(owner);
            result.put("class_name", owner);
            result.put("dex_entry", origins.get(owner));
            Set<String> seen = new HashSet<>();
            seen.add(owner);
            String current = cls.getSuperclass();
            int depth = 0;
            while (current != null && seen.add(current)) {
                page.add(Map.of("relation", "superclass", "type_descriptor", current,
                    "depth", ++depth, "definition_resolution", classes.containsKey(current)
                        ? "supplied" : "external"));
                current = classes.containsKey(current) ? classes.get(current).getSuperclass() : null;
            }
            result.put("hierarchy_cycle_detected", current != null);
            for (String type : new TreeSet<>(cls.getInterfaces()))
                page.add(Map.of("relation", "interface", "type_descriptor", type));
            for (ClassDef candidate : classes.values()) {
                if (owner.equals(candidate.getSuperclass()))
                    page.add(Map.of("relation", "direct_subclass", "type_descriptor", candidate.getType()));
                if (candidate.getInterfaces().contains(owner))
                    page.add(Map.of("relation", "direct_implementor", "type_descriptor", candidate.getType()));
            }
        } else {
            boolean constants = operation.equals("get_string_constants");
            long scanned = 0, withoutCode = 0;
            for (ClassDef cls : classes.values()) {
                if (!owner.isEmpty() && !owner.equals(cls.getType())) continue;
                TreeMap<String, Method> methods = new TreeMap<>();
                for (Method method : cls.getMethods()) {
                    if (methods.put(descriptor(method), method) != null)
                        throw new IllegalArgumentException("Duplicate method");
                }
                for (var row : methods.entrySet()) {
                    if (!requested.isEmpty() && !requested.equals(row.getKey())) continue;
                    Method method = row.getValue();
                    var implementation = method.getImplementation();
                    if (implementation == null) { withoutCode++; continue; }
                    BaksmaliOptions options = new BaksmaliOptions();
                    MethodDefinition renderer = constants ? null : new MethodDefinition(
                        new ClassDefinition(options, cls), method, implementation);
                    if (renderer != null) renderer.registerFormatter = new RegisterFormatter(
                        options, implementation.getRegisterCount(), MethodUtil.getParameterRegisterCount(method));
                    int address = 0;
                    for (Instruction instruction : implementation.getInstructions()) {
                        scanned++;
                        Map<String, Object> hit = new LinkedHashMap<>();
                        boolean matched = false;
                        if (constants) {
                            if (instruction instanceof ReferenceInstruction reference
                                    && (instruction.getOpcode().name.equals("const-string")
                                        || instruction.getOpcode().name.equals("const-string/jumbo"))) {
                                hit.put("value", ((StringReference) reference.getReference()).getString());
                                matched = true;
                            }
                        } else {
                            StringWriter buffer = new StringWriter();
                            BaksmaliWriter writer = new BaksmaliWriter(buffer);
                            InstructionMethodItemFactory.makeInstructionFormatMethodItem(
                                renderer, address, instruction).writeTo(writer);
                            writer.flush();
                            String rendered = buffer.toString();
                            matched = operation.equals("disassemble_method")
                                || (sensitive ? rendered : rendered.toLowerCase(Locale.ROOT)).contains(needle);
                            if (matched) hit.put("instruction", rendered);
                        }
                        if (matched) {
                            hit.put("class_name", cls.getType());
                            hit.put("method_descriptor", row.getKey());
                            hit.put("dex_entry", origins.get(cls.getType()));
                            hit.put("opcode", instruction.getOpcode().name);
                            hit.put("instruction_offset", address);
                            hit.put("offset_unit", "16_bit_code_units");
                            page.add(hit);
                        }
                        address = Math.addExact(address, instruction.getCodeUnits());
                    }
                }
            }
            result.put("scanned_instructions", scanned);
            result.put("methods_without_code", withoutCode);
            result.put("instruction_scan_complete", true);
            result.put("scan_errors", 0);
            if (!requested.isEmpty() && !methodsExist(classes.get(owner), requested))
                return Map.of("status", "error", "code", "method_not_found");
            result.put("match_semantics", operation.equals("disassemble_method") ? "exact_method_identity"
                : constants ? "const_string_operands_only"
                : (sensitive ? "case_sensitive" : "case_insensitive") + "_literal_baksmali_instruction_text");
        }
        result.put("items", page.items);
        result.put("total", page.total);
        return result;
    }

    static boolean methodsExist(ClassDef cls, String requested) {
        for (Method method : cls.getMethods()) if (descriptor(method).equals(requested)) return true;
        return false;
    }

    public static void main(String[] args) throws Exception {
        PrintStream output = System.out;
        System.setOut(System.err);
        output.write(new GsonBuilder().serializeNulls().create().toJson(run(args)).getBytes(StandardCharsets.UTF_8));
    }
}
