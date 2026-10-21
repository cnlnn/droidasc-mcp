import java.io.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;
import java.util.regex.*;
import com.google.gson.GsonBuilder;
import com.android.tools.smali.dexlib2.DexFileFactory;
import com.android.tools.smali.dexlib2.iface.*;
import jadx.api.JadxDecompiler;

/** Declaration-only comparisons and redacted string-pool candidate discovery. */
public class ReviewBridge {
    static final int MAX_RECORDS = 1000000;
    static final long MAX_INVENTORY_BYTES = 64L * 1024 * 1024;
    static long inventoryBytes = 0;

    static String descriptor(Method method) {
        StringBuilder value = new StringBuilder(method.getDefiningClass())
            .append("->").append(method.getName()).append('(');
        for (CharSequence type : method.getParameterTypes()) value.append(type);
        return value.append(')').append(method.getReturnType()).toString();
    }

    static class Declaration {
        String kind;
        String[] entries = new String[2];
        Declaration(String kind) { this.kind = kind; }
    }

    static void add(TreeMap<String, Declaration> rows, String kind, String identity, String entry, int side) {
        inventoryBytes += identity.getBytes(StandardCharsets.UTF_8).length + entry.length() + 32;
        if (inventoryBytes > MAX_INVENTORY_BYTES || (rows.size() >= MAX_RECORDS && !rows.containsKey(identity)))
            throw new IllegalArgumentException("inventory_limit");
        Declaration row = rows.computeIfAbsent(identity, key -> new Declaration(kind));
        if (row.entries[side] != null) throw new IllegalArgumentException("duplicate_declaration");
        row.entries[side] = entry;
    }

    static void inventory(String path, int side, String kind, TreeMap<String, Declaration> rows) throws Exception {
        var container = DexFileFactory.loadDexContainer(new File(path), null);
        var entries = new ArrayList<>(container.getDexEntryNames());
        Collections.sort(entries);
        for (String entry : entries) {
            for (ClassDef cls : container.getEntry(entry).getDexFile().getClasses()) {
                if (kind.equals("all") || kind.equals("class")) add(rows, "class", cls.getType(), entry, side);
                if (kind.equals("all") || kind.equals("method"))
                    for (Method method : cls.getMethods()) add(rows, "method", descriptor(method), entry, side);
                if (kind.equals("all") || kind.equals("field"))
                    for (Field field : cls.getFields()) add(rows, "field",
                        field.getDefiningClass() + "->" + field.getName() + ":" + field.getType(), entry, side);
            }
        }
    }

    static Map<String, Object> diff(String[] args) throws Exception {
        String kind = args[3], change = args[4];
        long offset = Long.parseLong(args[5]);
        int limit = Integer.parseInt(args[6]);
        TreeMap<String, Declaration> rows = new TreeMap<>();
        inventory(args[1], 0, kind, rows);
        inventory(args[2], 1, kind, rows);
        List<Map<String, Object>> items = new ArrayList<>();
        long total = 0, added = 0, removed = 0, unchanged = 0;
        for (var pair : rows.entrySet()) {
            Declaration row = pair.getValue();
            String state;
            if (row.entries[0] == null) { state = "added"; added++; }
            else if (row.entries[1] == null) { state = "removed"; removed++; }
            else { unchanged++; continue; }
            if (!change.equals("all") && !change.equals(state)) continue;
            if (total >= offset && total - offset < limit) {
                Map<String, Object> item = new LinkedHashMap<>();
                item.put("kind", row.kind);
                item.put("descriptor", pair.getKey());
                item.put("change", state);
                item.put("old_dex_entry", row.entries[0]);
                item.put("new_dex_entry", row.entries[1]);
                items.add(item);
            }
            total++;
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("status", "ok");
        result.put("items", items);
        result.put("total", total);
        result.put("counts", Map.of("added", added, "removed", removed, "unchanged", unchanged));
        result.put("ordering", "full_descriptor_lexicographic");
        result.put("scope", "class_and_member_identity_inventory_only");
        result.put("behavior_comparison", "not_performed");
        result.put("declaration_attributes_comparison", "not_performed");
        return result;
    }

    static final Map<String, Pattern> PATTERNS = new LinkedHashMap<>();
    static {
        PATTERNS.put("aws_access_key_id", Pattern.compile("(?<![A-Z0-9])(?:AKIA|ASIA)[A-Z0-9]{16}(?![A-Z0-9])"));
        PATTERNS.put("github_classic_token", Pattern.compile("(?<![A-Za-z0-9_])gh[pousr]_[A-Za-z0-9]{36}(?![A-Za-z0-9])"));
        PATTERNS.put("google_api_key", Pattern.compile("(?<![A-Za-z0-9_])AIza[0-9A-Za-z_-]{35}(?![A-Za-z0-9_-])"));
        PATTERNS.put("private_key_marker", Pattern.compile("-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----"));
        PATTERNS.put("credential_assignment", Pattern.compile("(?i)(?:api[_-]?key|client[_-]?secret|access[_-]?token)[ \\t]*[:=][ \\t]*[\"']?([A-Za-z0-9_./+~-]{16,256})"));
        PATTERNS.put("jwt_like", Pattern.compile("(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{8,2048}\\.[A-Za-z0-9_-]{8,4096}\\.[A-Za-z0-9_-]{8,2048}(?![A-Za-z0-9_-])"));
    }

    static String fingerprint(String value) throws Exception {
        byte[] digest = MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8));
        StringBuilder result = new StringBuilder();
        for (byte b : digest) result.append(String.format("%02x", b & 255));
        return result.toString();
    }

    static Map<String, Object> secrets(String[] args) throws Exception {
        String selected = args[2];
        long offset = Long.parseLong(args[3]), maximum = Long.parseLong(args[5]);
        int limit = Integer.parseInt(args[4]);
        if (!selected.equals("all") && !PATTERNS.containsKey(selected))
            throw new IllegalArgumentException("invalid_pattern");
        var container = DexFileFactory.loadDexContainer(new File(args[1]), null);
        var entries = new ArrayList<>(container.getDexEntryNames());
        Collections.sort(entries);
        List<Map<String, Object>> items = new ArrayList<>();
        long total = 0, bytes = 0, strings = 0, skipped = 0, capped = 0;
        for (String entry : entries) {
            var pool = container.getEntry(entry).getDexFile().getStringReferences();
            for (int index = 0; index < pool.size(); index++) {
                if (++strings > 2000000) throw new IllegalArgumentException("secret_scan_limit");
                String value = pool.get(index).getString();
                bytes += value.getBytes(StandardCharsets.UTF_8).length;
                if (bytes > maximum) throw new IllegalArgumentException("secret_scan_limit");
                if (value.length() > 65536) { skipped++; continue; }
                for (var pattern : PATTERNS.entrySet()) {
                    if (!selected.equals("all") && !selected.equals(pattern.getKey())) continue;
                    Matcher matcher = pattern.getValue().matcher(value);
                    int count = 0;
                    while (matcher.find()) {
                        if (++count > 20) { capped++; break; }
                        int group = pattern.getKey().equals("credential_assignment") ? 1 : 0;
                        String token = matcher.group(group);
                        if (total >= offset && total - offset < limit) {
                            items.add(Map.of("pattern", pattern.getKey(), "dex_entry", entry,
                                "string_index", index, "utf16_offset", matcher.start(group),
                                "length_utf16", token.length(), "candidate_sha256", fingerprint(token),
                                "redacted", "[REDACTED]", "confidence", "candidate"));
                        }
                        total++;
                    }
                }
            }
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("status", skipped > 0 || capped > 0 ? "partial" : "ok");
        result.put("items", items);
        result.put("total", total);
        result.put("scanned_strings", strings);
        result.put("scanned_utf8_bytes", bytes);
        result.put("skipped_oversize_strings", skipped);
        result.put("capped_pattern_string_pairs", capped);
        result.put("coverage_complete", skipped == 0 && capped == 0);
        result.put("scope", "dex_string_pool_fixed_patterns_only");
        result.put("credential_validity", "not_checked");
        result.put("instruction_use_sites", "not_resolved");
        result.put("pattern_version", 1);
        return result;
    }

    public static void main(String[] args) throws Exception {
        PrintStream output = System.out;
        System.setOut(System.err);
        Map<String, Object> result;
        try {
            if (!"1.5.5".equals(JadxDecompiler.getVersion()))
                result = Map.of("status", "error", "code", "unsupported_backend_version");
            else result = args[0].equals("diff") ? diff(args) : secrets(args);
        } catch (IllegalArgumentException ex) {
            String code = String.valueOf(ex.getMessage());
            if (!Set.of("inventory_limit", "duplicate_declaration", "invalid_pattern", "secret_scan_limit").contains(code))
                code = "malformed_dex";
            result = Map.of("status", "error", "code", "inventory_or_scan_error",
                "diagnostic", code);
        }
        output.write(new GsonBuilder().serializeNulls().create().toJson(result).getBytes(StandardCharsets.UTF_8));
    }
}
