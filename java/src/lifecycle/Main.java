package lifecycle;

import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.EOFException;
import java.nio.channels.FileChannel;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.time.Clock;
import java.util.HashMap;
import java.util.Map;

public final class Main {
    public static void main(String[] args) throws Exception {
        Map<String, String> options = new HashMap<>();
        if (args.length % 2 != 0) throw new IllegalArgumentException("Expected option/value pairs");
        for (int i = 0; i < args.length; i += 2) {
            if (!java.util.Set.of("--run-dir", "--mode", "--crash-after").contains(args[i])
                    || options.putIfAbsent(args[i], args[i + 1]) != null) throw new IllegalArgumentException("Invalid option");
        }
        Path directory = Path.of(options.get("--run-dir")).toAbsolutePath().normalize();
        String mode = options.get("--mode");
        if (!java.util.Set.of("actor", "operator", "doctor").contains(mode)) throw new IllegalArgumentException("Invalid mode");
        if (options.containsKey("--crash-after") && !options.get("--crash-after").equals("disable_login")
                && !options.get("--crash-after").matches("(before_intent|after_intent|after_service_commit|after_result):(disable_login|add_role_grants|create_collection_task|undo_role_grants)")) throw new IllegalArgumentException("Invalid crash hook");
        Files.createDirectories(directory);
        try (var lockChannel = FileChannel.open(directory.resolve("process.lock"), StandardOpenOption.CREATE, StandardOpenOption.WRITE);
             var lock = lockChannel.tryLock()) {
            if (lock == null) { System.err.println("RUN_DIRECTORY_BUSY"); System.exit(3); }
            if (mode.equals("doctor")) {
                Path temp = Files.createTempFile(directory, "atomic-", ".tmp");
                Path target = directory.resolve("atomic-check.xml");
                try {
                    Files.move(temp, target, StandardCopyOption.ATOMIC_MOVE);
                    System.out.println("Java " + Runtime.version() + "; atomic move supported on tested directory");
                } finally { Files.deleteIfExists(temp); Files.deleteIfExists(target); }
                return;
            }
            var kernel = new LifecycleKernel(directory, options.get("--crash-after"), Clock.systemUTC());
            var input = new DataInputStream(System.in);
            var output = new DataOutputStream(System.out);
            while (true) {
                int length;
                try { length = input.readInt(); } catch (EOFException end) { if (mode.equals("actor")) kernel.actorDisconnected(); return; }
                if (length < 1 || length > 65_536) { System.err.println("FRAME_SIZE_DENIED"); if (mode.equals("actor")) kernel.actorDisconnected(); return; }
                byte[] payload = input.readNBytes(length);
                if (payload.length != length) { if (mode.equals("actor")) kernel.actorDisconnected(); return; }
                String requestId = "0";
                Map<String, String> result;
                try {
                    var envelope = XmlCodec.read(payload, "request", true);
                    requestId = envelope.id();
                    result = kernel.dispatch(mode, envelope.fields());
                } catch (LifecycleKernel.Denied denied) {
                    result = Map.of("code", denied.code);
                } catch (IllegalArgumentException | org.xml.sax.SAXException bad) {
                    result = Map.of("code", "INVALID_ARGUMENTS");
                }
                byte[] encoded = XmlCodec.write("response", requestId, result);
                if (encoded.length > 65_536) throw new IllegalStateException("Response budget exceeded");
                output.writeInt(encoded.length); output.write(encoded); output.flush();
            }
        }
    }
}
