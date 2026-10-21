import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.android.tools.smali.dexlib2.DexFileFactory;
import com.android.tools.smali.dexlib2.iface.*;
import com.android.tools.smali.dexlib2.iface.instruction.*;
import com.android.tools.smali.dexlib2.iface.instruction.formats.UnknownInstruction;
import com.android.tools.smali.dexlib2.iface.reference.*;
import com.android.tools.smali.dexlib2.iface.value.*;
import jadx.api.JadxDecompiler;

/** Streams original DEX relationships. A complete trailer is required before index publication. */
public class IndexBridge {
    static final Gson JSON = new GsonBuilder().serializeNulls().create();
    static PrintWriter output;
    static String entry;
    static long edges;
    static long records;

    static String descriptor(MethodReference m) {
        StringBuilder s = new StringBuilder(m.getDefiningClass()).append("->").append(m.getName()).append('(');
        for (CharSequence t : m.getParameterTypes()) s.append(t);
        return s.append(')').append(m.getReturnType()).toString();
    }
    static String descriptor(FieldReference f) {
        return f.getDefiningClass() + "->" + f.getName() + ":" + f.getType();
    }
    static void emit(Map<String, Object> row) {
        output.println(JSON.toJson(row));
        if (++records % 1024 == 0 && output.checkError())
            throw new IllegalStateException("Index stream closed");
    }
    static void definition(String kind, String name) {
        emit(Map.of("record", "definition", "kind", kind, "descriptor", name, "dex_entry", entry));
    }
    static void edge(String kind, String source, String target, String relation, Map<String, Object> data) {
        data.put("dex_entry", entry);
        emit(Map.of("record", "edge", "kind", kind, "source", source, "target", target,
            "relation", relation, "data", data));
        edges++;
    }
    static void type(String source, String target, String relation, String detail, Long address) {
        if (target == null || target.equals("V")) return;
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("source", source);
        row.put("type_descriptor", target);
        row.put("relation", relation);
        row.put("detail", detail);
        row.put("instruction_offset", address);
        row.put("offset_unit", address == null ? null : "code_units_from_method_start");
        edge("type", source, target, relation, row);
    }
    static void proto(String source, MethodProtoReference p, String relation, String detail, Long address) {
        type(source, p.getReturnType(), relation, detail + ":return", address);
        int n = 0;
        for (CharSequence t : p.getParameterTypes())
            type(source, t.toString(), relation, detail + ":parameter:" + n++, address);
    }
    static void memberTypes(String source, Reference ref, String relation, String detail, Long address) {
        if (ref instanceof TypeReference t) type(source, t.getType(), relation, detail, address);
        else if (ref instanceof FieldReference f) {
            type(source, f.getDefiningClass(), relation, detail + ":owner", address);
            type(source, f.getType(), relation, detail + ":field_type", address);
        } else if (ref instanceof MethodReference m) {
            type(source, m.getDefiningClass(), relation, detail + ":owner", address);
            type(source, m.getReturnType(), relation, detail + ":return", address);
            int n = 0;
            for (CharSequence t : m.getParameterTypes())
                type(source, t.toString(), relation, detail + ":parameter:" + n++, address);
        } else if (ref instanceof MethodProtoReference p) proto(source, p, relation, detail, address);
    }
    static void value(String source, EncodedValue v, String path, int depth) {
        if (depth > 128) throw new IllegalArgumentException("Annotation nesting exceeds limit");
        if (v instanceof TypeEncodedValue t) type(source, t.getValue(), "annotation", path, null);
        else if (v instanceof EnumEncodedValue f) memberTypes(source, f.getValue(), "annotation", path, null);
        else if (v instanceof FieldEncodedValue f) memberTypes(source, f.getValue(), "annotation", path, null);
        else if (v instanceof MethodEncodedValue m) memberTypes(source, m.getValue(), "annotation", path, null);
        else if (v instanceof MethodTypeEncodedValue p) proto(source, p.getValue(), "annotation", path, null);
        else if (v instanceof ArrayEncodedValue a) {
            int n = 0;
            for (EncodedValue item : a.getValue()) value(source, item, path + "[" + n++ + "]", depth + 1);
        } else if (v instanceof AnnotationEncodedValue a) {
            type(source, a.getType(), "annotation", path + ":type", null);
            for (AnnotationElement e : sorted(a.getElements())) value(source, e.getValue(), path + "." + e.getName(), depth + 1);
        }
    }
    static List<AnnotationElement> sorted(Set<? extends AnnotationElement> elements) {
        List<AnnotationElement> result = new ArrayList<>(elements);
        result.sort(Comparator.comparing(AnnotationElement::getName));
        return result;
    }
    static void annotations(String source, Set<? extends Annotation> annotations, String location) {
        List<Annotation> ordered = new ArrayList<>(annotations);
        ordered.sort(Comparator.comparing(Annotation::getType));
        for (Annotation a : ordered) {
            String path = location + ":" + a.getType();
            type(source, a.getType(), "annotation", path + ":type", null);
            for (AnnotationElement e : sorted(a.getElements())) value(source, e.getValue(), path + "." + e.getName(), 0);
        }
    }
    static void method(Method m) {
        String source = descriptor(m);
        definition("method", source);
        type(source, m.getReturnType(), "declaration", "return", null);
        annotations(source, m.getAnnotations(), "method");
        int n = 0;
        for (MethodParameter p : m.getParameters()) {
            type(source, p.getType(), "declaration", "parameter:" + n, null);
            annotations(source, p.getAnnotations(), "parameter:" + n++);
        }
        MethodImplementation impl = m.getImplementation();
        long count = 0, address = 0;
        if (impl != null) {
            for (TryBlock<? extends ExceptionHandler> block : impl.getTryBlocks())
                for (ExceptionHandler handler : block.getExceptionHandlers())
                    type(source, handler.getExceptionType(), "instruction", "catch", (long) handler.getHandlerCodeAddress());
            for (Instruction insn : impl.getInstructions()) {
                if (insn instanceof UnknownInstruction || insn.getOpcode().odexOnly())
                    throw new IllegalArgumentException("Unknown or optimized DEX instruction");
                count++;
                String opcode = insn.getOpcode().name;
                if (insn instanceof ReferenceInstruction r) {
                    Reference ref = r.getReference();
                    Map<String, Object> row = new LinkedHashMap<>();
                    row.put("caller", source);
                    row.put("instruction_offset", address);
                    row.put("offset_unit", "code_units_from_method_start");
                    row.put("opcode", opcode);
                    if (ref instanceof MethodReference target) {
                        row.put("callee", descriptor(target));
                        if (insn instanceof DualReferenceInstruction dual && dual.getReference2() instanceof MethodProtoReference p) {
                            StringBuilder sig = new StringBuilder("(");
                            for (CharSequence t : p.getParameterTypes()) sig.append(t);
                            row.put("call_site_prototype", sig.append(')').append(p.getReturnType()).toString());
                        }
                        edge("method", source, descriptor(target), "instruction", row);
                    } else if (ref instanceof FieldReference target) {
                        String access;
                        if (opcode.startsWith("iget") || opcode.startsWith("sget")) access = "read";
                        else if (opcode.startsWith("iput") || opcode.startsWith("sput")) access = "write";
                        else throw new IllegalArgumentException("Unknown field access opcode");
                        row.put("field_descriptor", descriptor(target));
                        row.put("access", access);
                        row.put("storage", opcode.startsWith("s") ? "static" : "instance");
                        edge("field", source, descriptor(target), access, row);
                    }
                    memberTypes(source, ref, "instruction", opcode, address);
                    if (insn instanceof DualReferenceInstruction dual)
                        memberTypes(source, dual.getReference2(), "instruction", opcode + ":prototype", address);
                    if (ref instanceof CallSiteReference || ref instanceof MethodHandleReference || opcode.startsWith("invoke-polymorphic"))
                        emit(Map.of("record", "dynamic", "source", source, "data", Map.of(
                            "caller", source, "dex_entry", entry, "instruction_offset", address,
                            "opcode", opcode, "reason", "dynamic_target_not_resolved")));
                }
                address += insn.getCodeUnits();
            }
        }
        emit(Map.of("record", "method", "source", source, "instructions", count, "without_code", impl == null ? 1 : 0));
    }
    public static void main(String[] args) throws Exception {
        output = new PrintWriter(new BufferedWriter(new OutputStreamWriter(System.out, StandardCharsets.UTF_8)));
        System.setOut(System.err);
        if (!"1.5.5".equals(JadxDecompiler.getVersion())) throw new IllegalArgumentException("Expected JADX 1.5.5");
        var container = DexFileFactory.loadDexContainer(new File(args[0]), null);
        var entries = new ArrayList<>(container.getDexEntryNames());
        Collections.sort(entries);
        for (String name : entries) {
            entry = name;
            TreeMap<String, ClassDef> classes = new TreeMap<>();
            for (ClassDef c : container.getEntry(entry).getDexFile().getClasses()) {
                if (classes.put(c.getType(), c) != null) throw new IllegalArgumentException("Duplicate class");
            }
            for (ClassDef c : classes.values()) {
                definition("type", c.getType());
                type(c.getType(), c.getSuperclass(), "declaration", "superclass", null);
                for (String t : c.getInterfaces()) type(c.getType(), t, "declaration", "interface", null);
                annotations(c.getType(), c.getAnnotations(), "class");
                TreeMap<String, Field> fields = new TreeMap<>();
                for (Field f : c.getFields()) {
                    if (fields.put(descriptor(f), f) != null) throw new IllegalArgumentException("Duplicate field");
                }
                for (Field f : fields.values()) {
                    definition("field", descriptor(f));
                    type(descriptor(f), f.getType(), "declaration", "field_type", null);
                    annotations(descriptor(f), f.getAnnotations(), "field");
                }
                TreeMap<String, Method> methods = new TreeMap<>();
                for (Method m : c.getMethods()) {
                    if (methods.put(descriptor(m), m) != null) throw new IllegalArgumentException("Duplicate method");
                }
                for (Method m : methods.values()) method(m);
            }
        }
        emit(Map.of("record", "complete", "edges", edges, "schema", 1));
        if (output.checkError()) throw new IllegalStateException("Index stream closed");
    }
}
