import java.io.File;
import java.util.*;
import com.android.tools.smali.dexlib2.DexFileFactory;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedMethodImplementation;
import com.android.tools.smali.dexlib2.dexbacked.DexBackedMethod;
import com.android.tools.smali.dexlib2.dexbacked.raw.MethodIdItem;
import com.android.tools.smali.dexlib2.dexbacked.instruction.DexBackedInstruction;
import com.android.tools.smali.dexlib2.iface.instruction.*;
import com.android.tools.smali.dexlib2.iface.instruction.formats.ArrayPayload;

/** Independent comparison against the library's unfiltered instruction iterator. */
public class InstructionCursorOracle {
    public static void main(String[] args) throws Exception {
        long checked = 0;
        for (String path : args) {
            var container = DexFileFactory.loadDexContainer(new File(path), null);
            for (String entry : container.getDexEntryNames()) {
                var dex = container.getEntry(entry).getDexFile();
                var table = MethodBridge.InstructionCursor.table(dex.getOpcodes());
                var names = new MethodBridge.MemberNames(dex);
                for (int index = 0; index < dex.getFieldSection().size(); index++)
                    if (!names.member(index, true).equals(MethodBridge.descriptor(dex.getFieldSection().get(index))))
                        throw new AssertionError("Field pool mismatch");
                for (int index = 0; index < dex.getMethodSection().size(); index++)
                    if (!names.member(index, false).equals(MethodBridge.descriptor(dex.getMethodSection().get(index))))
                        throw new AssertionError("Method pool mismatch");
                for (var cls : dex.getClasses()) for (var method : cls.getMethods()) {
                    var impl = method.getImplementation();
                    if (impl == null) continue;
                    var cursor = new MethodBridge.InstructionCursor(impl, table);
                    long address = 0;
                    for (var expected : impl.getInstructions()) {
                        if (!cursor.advance() || cursor.opcode != expected.getOpcode()
                                || cursor.address != address
                                || cursor.units != expected.getCodeUnits())
                            throw new AssertionError("Instruction boundary mismatch: " + method);
                        if (expected instanceof ReferenceInstruction reference) {
                            var actual = (ReferenceInstruction) cursor.instruction();
                            if (!actual.getReference().equals(reference.getReference()))
                                throw new AssertionError("Operand mismatch: " + method);
                            if (expected instanceof DualReferenceInstruction dual
                                    && !((DualReferenceInstruction) actual).getReference2()
                                        .equals(dual.getReference2()))
                                throw new AssertionError("Second operand mismatch: " + method);
                        }
                        if (expected instanceof ArrayPayload) {
                            var backed = (DexBackedMethodImplementation) impl;
                            var payload = (DexBackedInstruction) expected;
                            var bytes = backed.dexFile.getDataBuffer().getBuf();
                            int pos = backed.dexFile.getDataBuffer().getBaseOffset() + payload.instructionStart;
                            byte[] saved = Arrays.copyOfRange(bytes, pos, pos + 8);
                            // A positive int-wrapped payload length must not cross the code-item end.
                            bytes[pos + 2] = 8;
                            bytes[pos + 3] = 0;
                            Arrays.fill(bytes, pos + 4, pos + 7, (byte) 0xff);
                            bytes[pos + 7] = 0x7f;
                            boolean failed = false;
                            try {
                                var invalid = new MethodBridge.InstructionCursor(impl);
                                while (invalid.advance()) { }
                            } catch (RuntimeException error) { failed = true; }
                            finally { System.arraycopy(saved, 0, bytes, pos, saved.length); }
                            if (!failed) throw new AssertionError("Accepted overflowing payload");
                        }
                        checked++;
                        address += expected.getCodeUnits();
                    }
                    if (cursor.advance()) throw new AssertionError("Unexpected trailing instruction");
                    if (method.getName().equals("aNoReference")) {
                        var pool = dex.getBuffer();
                        int protoPosition = pool.getBaseOffset() + dex.getMethodSection()
                            .getOffset(((DexBackedMethod) method).methodIndex) + MethodIdItem.PROTO_OFFSET;
                        byte[] poolBytes = pool.getBuf();
                        byte low = poolBytes[protoPosition], highProto = poolBytes[protoPosition + 1];
                        boolean invalidProtoFailed = false;
                        try {
                            poolBytes[protoPosition] = poolBytes[protoPosition + 1] = (byte) 0xff;
                            new MethodBridge.MethodKey(method, new MethodBridge.MemberNames(dex));
                        } catch (RuntimeException error) { invalidProtoFailed = true; }
                        finally { poolBytes[protoPosition] = low; poolBytes[protoPosition + 1] = highProto; }
                        if (!invalidProtoFailed) throw new AssertionError("Accepted invalid unreferenced prototype");
                        var backed = (DexBackedMethodImplementation) impl;
                        var first = (DexBackedInstruction) impl.getInstructions().iterator().next();
                        var bytes = backed.dexFile.getDataBuffer().getBuf();
                        int start = backed.dexFile.getDataBuffer().getBaseOffset() + first.instructionStart;
                        byte saved = bytes[start];
                        // Unknown opcode, oversized fixed instruction, and truncated payload.
                        for (int opcode : new int[] {0x73, 0x14, 0x00}) {
                            bytes[start] = (byte) opcode;
                            byte high = bytes[start + 1];
                            bytes[start + 1] = (byte) (opcode == 0 ? 3 : 0);
                            boolean failed = false;
                            try {
                                var invalid = new MethodBridge.InstructionCursor(impl);
                                while (invalid.advance()) { }
                            } catch (RuntimeException error) { failed = true; }
                            finally { bytes[start] = saved; bytes[start + 1] = high; }
                            if (!failed) throw new AssertionError("Accepted invalid opcode " + opcode);
                        }
                    }
                }
            }
        }
        if (checked < 20) throw new AssertionError("Insufficient instruction coverage");
        System.out.println("checked=" + checked);
    }
}
