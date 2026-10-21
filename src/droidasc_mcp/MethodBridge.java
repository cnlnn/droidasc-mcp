import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import com.google.gson.Gson;
import com.android.tools.smali.dexlib2.DexFileFactory;
import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.iface.*;
import com.android.tools.smali.baksmali.BaksmaliOptions;
import com.android.tools.smali.baksmali.Adaptors.ClassDefinition;
import com.android.tools.smali.baksmali.Adaptors.MethodDefinition;
import com.android.tools.smali.baksmali.formatter.BaksmaliWriter;
import jadx.api.*;

/** Isolated optional backend. Identity comes from DEX, never decompiled Java text. */
public class MethodBridge {
    static String descriptor(Method method) {
        StringBuilder result = new StringBuilder(method.getDefiningClass())
            .append("->").append(method.getName()).append('(');
        for (CharSequence type : method.getParameterTypes()) result.append(type);
        return result.append(')').append(method.getReturnType()).toString();
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
        ClassDef owner = null;
        var dex = DexFileFactory.loadDexEntry(input, entry, true, Opcodes.getDefault()).getDexFile();
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

    public static void main(String[] args) throws Exception {
        PrintStream output = System.out;
        System.setOut(System.err);
        Map<String, Object> result = run(args);
        output.write(new Gson().toJson(result).getBytes(StandardCharsets.UTF_8));
    }
}
