package lifecycle;

import java.util.HashMap;
import java.util.Map;

/** Three explicit local service adapters, with independent commits and receipts. */
final class Services {
    record Receipt(long version, boolean replay) {}

    abstract static class Service {
        final SnapshotStore store;
        Service(SnapshotStore store) { this.store = store; }
        Map<String, String> read() { return store.read(); }

        Receipt apply(String action, String operation, String payloadHash, long expectedVersion, Map<String,String> authority) throws Exception {
            var state = read();
            String receiptKey = ledgerKey(operation, action);
            if (state.containsKey(receiptKey)) {
                if (!state.get(receiptKey).equals(operation + ":" + payloadHash)) {
                    throw new LifecycleKernel.Denied("IDEMPOTENCY_CONFLICT");
                }
                return new Receipt(Long.parseLong(state.get("version")), true);
            }
            if (Long.parseLong(state.get("version")) != expectedVersion) {
                throw new LifecycleKernel.Denied("STALE_APPROVAL");
            }
            boolean changed = mutate(action, state, operation);
            state.put(receiptKey, operation + ":" + payloadHash);
            state.put("receipt." + action, operation + ":" + payloadHash);
            state.put("effects." + action, changed ? "1" : "0");
            state.put(receiptKey.replace("ledger.", "effect."), changed ? "1" : "0");
            state.put(receiptKey.replace("ledger.", "audit."), authority.get("commit_order") + "|" + authority.get("event_sequence") + "|" + authority.get("epoch") + "|" + authority.get("intent") + "|" + authority.get("commit_time") + "|" + authority.get("execution_mode"));
            state.put("commit_order", authority.get("commit_order"));
            state.put("version", Long.toString(Math.addExact(expectedVersion, 1)));
            store.save(state); // business state and dedupe receipt commit together
            return new Receipt(expectedVersion + 1, false);
        }

        abstract boolean mutate(String action, Map<String, String> state, String operation) throws Exception;
    }

    static String ledgerKey(String operation, String action) {
        String workflow = operation.substring(0, operation.indexOf('/'));
        return "ledger." + workflow.substring(workflow.lastIndexOf('-') + 1) + "." + action;
    }

    static final class Identity extends Service {
        private final String approvedGrants;
        private final String targetGrants;
        Identity(SnapshotStore store, String approvedGrants) { this(store, approvedGrants, approvedGrants); }
        Identity(SnapshotStore store, String approvedGrants, String targetGrants) {
            super(store); this.approvedGrants = approvedGrants; this.targetGrants = targetGrants;
        }
        @Override boolean mutate(String action, Map<String, String> state, String operation) throws Exception {
            switch (action) {
                case "prepare_account": {
                    if (state.getOrDefault("account_exists", "true").equals("true")) return false;
                    state.put("account_exists", "true"); state.put("account_state", "PREPARED");
                    state.put("created_by", workflowOf(operation)); state.put("enabled", "false");
                    return true;
                }
                case "add_role_grants": {
                    var existing = grantSet(state.get("grants"));
                    var added = grantSet(targetGrants); added.removeAll(existing);
                    existing.addAll(added);
                    state.put("grants", String.join(",", existing));
                    state.put("added_grants", String.join(",", added));
                    state.put("grants_added_by", workflowOf(operation));
                    return !added.isEmpty();
                }
                case "enable_login": {
                    if (!state.get("grants").equals(targetGrants)) throw new LifecycleKernel.Denied("ROLE_POSTCONDITION_FAILED");
                    if (state.get("enabled").equals("true")) throw new LifecycleKernel.Denied("ACCOUNT_ALREADY_ENABLED");
                    state.put("enabled", "true"); state.put("enabled_by", workflowOf(operation));
                    state.put("account_state", "ACTIVE");
                    return true;
                }
                case "compensate_account": {
                    String owner = workflowOf(operation);
                    boolean changed = false;
                    if (state.getOrDefault("enabled_by", "").equals(owner)) {
                        changed = state.get("enabled").equals("true") || !state.get("sessions").equals("0");
                        state.put("enabled", "false"); state.put("sessions", "0"); state.put("enabled_by", "");
                        if (!state.getOrDefault("created_by", "").equals(owner)) state.put("account_state", "INACTIVE");
                    }
                    if (state.getOrDefault("created_by", "").equals(owner) && !state.getOrDefault("account_state", "").equals("TOMBSTONE")) {
                        state.put("account_state", "TOMBSTONE"); changed = true;
                    }
                    return changed;
                }
                case "undo_role_grants": {
                    if (!state.getOrDefault("grants_added_by", "").equals(workflowOf(operation))) return false;
                    var grants = grantSet(state.get("grants"));
                    boolean changed = grants.removeAll(grantSet(state.getOrDefault("added_grants", "")));
                    state.put("grants", String.join(",", grants));
                    state.put("added_grants", ""); state.put("grants_added_by", "");
                    return changed;
                }
                case "disable_login": {
                    boolean changed = state.get("enabled").equals("true");
                    state.put("enabled", "false");
                    return changed;
                }
                case "revoke_sessions": {
                    boolean changed = !state.get("sessions").equals("0");
                    state.put("sessions", "0");
                    return changed;
                }
                case "remove_grants": {
                    if (!state.get("grants").equals(approvedGrants)) throw new LifecycleKernel.Denied("STALE_APPROVAL");
                    boolean changed = !state.get("grants").isEmpty();
                    state.put("grants", "");
                    return changed;
                }
                default: throw new LifecycleKernel.Denied("UNKNOWN_STEP");
            }
        }
    }

    static final class Assets extends Service {
        Assets(SnapshotStore store) { super(store); }
        @Override boolean mutate(String action, Map<String, String> state, String operation) throws Exception {
            if (action.equals("reserve_asset")) {
                if (!state.get("asset_id").isEmpty() || !state.getOrDefault("inventory_available", "true").equals("true")) {
                    throw new LifecycleKernel.Denied("ASSET_UNAVAILABLE");
                }
                state.put("asset_id", state.get("inventory_id")); state.put("reserved_by", workflowOf(operation));
                state.put("inventory_available", "false"); return true;
            }
            if (action.equals("release_asset")) {
                if (!state.getOrDefault("reserved_by", "").equals(workflowOf(operation))) return false;
                state.put("asset_id", ""); state.put("reserved_by", "");
                state.put("inventory_available", "true"); return true;
            }
            if (!action.equals("create_collection_task")) throw new LifecycleKernel.Denied("UNKNOWN_STEP");
            if (state.get("asset_id").isEmpty()) return false;
            if (!state.get("collection_task").isEmpty()) throw new LifecycleKernel.Denied("CONFLICTING_COLLECTION_TASK");
            state.put("collection_task", "collect-" + state.get("employee_id") + "-" + state.get("asset_id"));
            state.put("collection_status", "OPEN");
            return true;
        }
    }

    static final class Hr extends Service {
        Hr(SnapshotStore store) { super(store); }
        @Override boolean mutate(String action, Map<String, String> state, String operation) throws Exception {
            String target = switch (action) {
                case "complete_hr" -> "OFFBOARDED";
                case "complete_onboarding_hr" -> "ONBOARDED";
                case "fail_onboarding_hr" -> "ONBOARDING_FAILED";
                default -> throw new LifecycleKernel.Denied("UNKNOWN_STEP");
            };
            state.put("administrative_status", target);
            return true;
        }
    }

    static Map<String, String> seed(String employee, String... entries) {
        Map<String, String> state = new HashMap<>();
        state.put("employee_id", employee);
        state.put("version", "1");
        state.put("commit_order", "0");
        for (int i = 0; i < entries.length; i += 2) state.put(entries[i], entries[i + 1]);
        return state;
    }

    private static String workflowOf(String operation) { return operation.substring(0, operation.indexOf('/')); }
    private static java.util.TreeSet<String> grantSet(String csv) {
        var result = new java.util.TreeSet<String>();
        if (!csv.isEmpty()) result.addAll(java.util.Arrays.asList(csv.split(",")));
        return result;
    }
}
