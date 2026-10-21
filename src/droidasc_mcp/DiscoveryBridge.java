import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import com.google.gson.GsonBuilder;
import com.android.tools.smali.dexlib2.DexFileFactory;
import com.android.tools.smali.dexlib2.iface.*;
import jadx.api.JadxDecompiler;

/** Declaration and string-pool discovery without decoding method instructions. */
public class DiscoveryBridge {
    static String descriptor(Method method) {
        StringBuilder value = new StringBuilder(method.getDefiningClass())
            .append("->").append(method.getName()).append('(');
        for (CharSequence type : method.getParameterTypes()) value.append(type);
        return value.append(')').append(method.getReturnType()).toString();
    }

    static Map<String, Object> run(String[] args) throws Exception {
        String operation = args[1], kind = args[2], needle = args[3], owner = args[4];
        long offset = Long.parseLong(args[5]);
        int limit = Integer.parseInt(args[6]);
        if (!"1.5.5".equals(JadxDecompiler.getVersion()))
            return Map.of("status", "error", "code", "unsupported_backend_version");
        var container = DexFileFactory.loadDexContainer(new File(args[0]), null);
        var entries = new ArrayList<>(container.getDexEntryNames());
        Collections.sort(entries);
        List<Map<String, Object>> items = new ArrayList<>();
        long total = 0;
        boolean strings = operation.equals("search_strings");
        if (strings) {
            for (String entry : entries) {
                var pool = container.getEntry(entry).getDexFile().getStringReferences();
                for (int index = 0; index < pool.size(); index++) {
                    String value = pool.get(index).getString();
                    if (!value.contains(needle)) continue;
                    if (total >= offset && total - offset < limit)
                        items.add(Map.of("dex_entry", entry, "string_index", index, "value", value));
                    total++;
                }
            }
        } else {
            TreeMap<String, ClassDef> classes = new TreeMap<>();
            Map<String, String> sources = new HashMap<>();
            for (String entry : entries) {
                for (ClassDef cls : container.getEntry(entry).getDexFile().getClasses()) {
                    if (!owner.isEmpty() && !owner.equals(cls.getType())) continue;
                    if (classes.put(cls.getType(), cls) != null)
                        throw new IllegalArgumentException("Duplicate class definition");
                    sources.put(cls.getType(), entry);
                }
            }
            for (ClassDef cls : classes.values()) {
                TreeSet<String> members = new TreeSet<>();
                if (kind.equals("method")) {
                    for (Method method : cls.getMethods()) {
                        if (!members.add(descriptor(method)))
                            throw new IllegalArgumentException("Duplicate method definition");
                    }
                } else if (kind.equals("field")) {
                    for (Field field : cls.getFields()) {
                        if (!members.add(field.getDefiningClass() + "->" + field.getName() + ":" + field.getType()))
                            throw new IllegalArgumentException("Duplicate field definition");
                    }
                } else throw new IllegalArgumentException("Unknown member kind");
                for (String value : members) {
                    if (!value.contains(needle)) continue;
                    if (total >= offset && total - offset < limit)
                        items.add(Map.of("kind", kind, "descriptor", value,
                            "dex_entry", sources.get(cls.getType())));
                    total++;
                }
            }
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("status", "ok");
        result.put("backend", "dexlib2-discovery");
        result.put("backend_version", JadxDecompiler.getVersion());
        result.put("instruction_scan_complete", false);
        result.put("scan_errors", 0);
        result.put("runtime_target_resolution", "not_performed");
        result.put("match_semantics", strings ? "case_sensitive_literal_substring_of_string_value"
            : "case_sensitive_literal_substring_of_full_descriptor");
        result.put("scope", strings ? "string_pool_in_supplied_files" : "declarations_in_supplied_files");
        result.put("items", items);
        result.put("total", total);
        return result;
    }

    public static void main(String[] args) throws Exception {
        PrintStream output = System.out;
        System.setOut(System.err);
        output.write(new GsonBuilder().serializeNulls().create().toJson(run(args)).getBytes(StandardCharsets.UTF_8));
    }
}
