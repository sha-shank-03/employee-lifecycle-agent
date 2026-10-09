package lifecycle;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;

/** Runs in JDK source-file mode before the application is built. */
public final class AtomicMoveDoctor {
    public static void main(String[] args) throws Exception {
        Path directory = Path.of(args[0]);
        Files.createDirectories(directory);
        Path temp = Files.createTempFile(directory, "doctor-", ".tmp");
        Path committed = directory.resolve("committed.xml");
        try {
            Files.writeString(temp, "atomic move check");
            Files.move(temp, committed, StandardCopyOption.ATOMIC_MOVE);
            if (!Files.readString(committed).equals("atomic move check")) throw new AssertionError("Atomic move content mismatch");
            System.out.println("ATOMIC_MOVE_SUPPORTED");
        } finally {
            Files.deleteIfExists(temp);
            Files.deleteIfExists(committed);
        }
    }
}
