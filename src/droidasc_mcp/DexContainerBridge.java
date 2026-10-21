import java.io.*;
import java.nio.file.*;
import java.util.*;
import com.google.gson.Gson;
import com.android.tools.smali.dexlib2.Opcodes;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedDexFile;
import com.android.tools.smali.dexlib2.iface.*;
import com.android.tools.smali.dexlib2.writer.pool.DexPool;
import com.android.tools.smali.dexlib2.writer.io.DexDataStore;
import com.android.tools.smali.dexlib2.writer.io.FileDataStore;
import jadx.api.JadxDecompiler;

/** Re-encode one logical DEX while retaining physical container offsets during reading. */
public class DexContainerBridge {
    static class LogicalDex extends DexBackedDexFile {
        LogicalDex(byte[] data, int header) { super(null, data, 0, true, header); }
    }
    static class BoundedStore implements DexDataStore {
        final FileDataStore delegate;
        final long maximum;
        BoundedStore(String path, long maximum) throws IOException {
            delegate = new FileDataStore(new File(path));
            this.maximum = maximum;
        }
        public OutputStream outputAt(int offset) {
            OutputStream stream = delegate.outputAt(offset);
            return new FilterOutputStream(stream) {
                long position = offset;
                void reserve(int count) throws IOException {
                    if (position < 0 || count < 0 || position + count > maximum)
                        throw new IOException("Normalized DEX exceeds reserved byte budget");
                    position += count;
                }
                public void write(int value) throws IOException { reserve(1); out.write(value); }
                public void write(byte[] data, int start, int count) throws IOException {
                    reserve(count); out.write(data, start, count);
                }
            };
        }
        public InputStream readAt(int offset) { return delegate.readAt(offset); }
        public void close() throws IOException { delegate.close(); }
    }
    public static void main(String[] args) throws Exception {
        if (!"1.5.5".equals(JadxDecompiler.getVersion()))
            throw new IllegalArgumentException("Expected JADX 1.5.5");
        byte[] data = Files.readAllBytes(Path.of(args[0]));
        var logical = new LogicalDex(data, Integer.parseInt(args[1]));
        DexFile standalone = new DexFile() {
            public Opcodes getOpcodes() { return Opcodes.forDexVersion(40); }
            public Set<? extends ClassDef> getClasses() { return logical.getClasses(); }
        };
        BoundedStore store = new BoundedStore(args[2], Long.parseLong(args[3]));
        try { DexPool.writeTo(store, standalone); } finally { store.close(); }
        System.out.print(new Gson().toJson(Map.of("status", "ok")));
    }
}
