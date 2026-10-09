package lifecycle;

import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.util.HashMap;
import java.util.Map;

/** Immutable small generation files; only process-restart durability is claimed. */
final class SnapshotStore {
    private final Path directory;
    private long generation;
    private Map<String, String> state;

    SnapshotStore(Path runDirectory, String name) throws Exception {
        directory = runDirectory.resolve(name);
        Files.createDirectories(directory);
        try (var stream = Files.list(directory)) {
            var latest = stream.filter(p -> p.getFileName().toString().matches("[0-9]{20}\\.xml"))
                    .max(java.util.Comparator.comparing(p -> p.getFileName().toString()));
            if (latest.isPresent()) {
                var path = latest.get();
                generation = Long.parseLong(path.getFileName().toString().substring(0, 20));
                if (Files.size(path) > 4 * 1024 * 1024) throw new IllegalStateException("Oversized committed snapshot");
                state = XmlCodec.read(Files.readAllBytes(path), "snapshot", false).fields();
            }
        }
    }

    boolean exists() { return state != null; }
    Map<String, String> read() {
        if (state == null) throw new IllegalStateException("Run directory is not initialized");
        return new HashMap<>(state);
    }

    void save(Map<String, String> next) throws Exception {
        byte[] bytes = XmlCodec.write("snapshot", "", next);
        long committedBytes;
        try (var files = Files.list(directory)) {
            committedBytes = files.filter(p -> p.getFileName().toString().matches("[0-9]{20}\\.xml"))
                    .mapToLong(p -> { try { return Files.size(p); } catch (java.io.IOException e) { throw new java.io.UncheckedIOException(e); } }).sum();
        }
        if (bytes.length > 4 * 1024 * 1024 || generation >= 4096 || committedBytes + bytes.length > 16 * 1024 * 1024) {
            throw new IllegalStateException("Snapshot budget exceeded");
        }
        long nextGeneration = Math.addExact(generation, 1);
        Path target = directory.resolve(String.format("%020d.xml", nextGeneration));
        Path temp = Files.createTempFile(directory, "pending-", ".tmp");
        try {
            try (var channel = FileChannel.open(temp, StandardOpenOption.WRITE)) {
                var buffer = ByteBuffer.wrap(bytes);
                while (buffer.hasRemaining()) channel.write(buffer);
                channel.force(true);
            }
            Files.move(temp, target, StandardCopyOption.ATOMIC_MOVE);
            state = new HashMap<>(next);
            generation = nextGeneration;
        } finally {
            Files.deleteIfExists(temp);
        }
    }
}
