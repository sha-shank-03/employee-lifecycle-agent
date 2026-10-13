package lifecycle;

import java.io.ByteArrayOutputStream;
import java.io.DataOutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.time.Clock;
import java.time.Instant;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

/** Finite lifecycle authority; all payloads, approval and safety work live here. */
final class LifecycleKernel {
    static final List<String> STEPS = List.of("disable_login", "revoke_sessions", "remove_grants", "create_collection_task", "complete_hr");
    static final List<String> JOIN = List.of("prepare_account", "add_role_grants", "reserve_asset", "enable_login", "complete_onboarding_hr");
    static final List<String> CLEANUP = List.of("compensate_account", "undo_role_grants", "release_asset", "fail_onboarding_hr");
    static final Map<String,String> BUNDLES = Map.of("engineer","employees,engineering","support","employees,support");
    static final Set<String> ACTOR_TOOLS = Set.of("inspect_employee","read_policy","propose_plan","workflow_status","execute_step","verify_outcome","request_handoff","begin_turn","charge_wait","stop_actor");
    static final Set<String> OPERATOR_TOOLS = Set.of("init","review","approve","report","cancel","import_event","activate_event","advance_clock");
    static final Set<String> RUNNING = Set.of("RUNNING","RETRY_PENDING");
    private final SnapshotStore workflows, hrStore, identityStore, assetStore;
    private final Path runDirectory;
    private final String crashAfter;
    private final Clock clock;
    static final class Denied extends Exception {
        final String code;
        Denied(String code) { super(code); this.code = code; }
    }

    LifecycleKernel(Path directory, String crashAfter, Clock clock) throws Exception {
        runDirectory=directory; this.crashAfter=crashAfter; this.clock=clock;
        workflows=new SnapshotStore(directory,"workflow"); hrStore=new SnapshotStore(directory,"hr");
        identityStore=new SnapshotStore(directory,"identity"); assetStore=new SnapshotStore(directory,"assets");
        long count=List.of(workflows,hrStore,identityStore,assetStore).stream().filter(SnapshotStore::exists).count();
        if (count!=0 && count!=4) throw new IllegalStateException("Partial initialization; use a fresh directory");
        if (count==4) {
            validateCommittedState(); reconcile();
            var s=workflows.read();
            if (!sameEvent(s)) safetyStop("SUPERSEDED");
            else if (Set.of("COMPENSATING","SAFETY_REVOKING").contains(s.get("administrative_status"))) runSafety();
            else if (RUNNING.contains(s.get("administrative_status")) && forward(s).stream().allMatch(a->done(s,a))) verify();
        }
    }
    Map<String,String> dispatch(String mode, Map<String,String> r) throws Exception {
        String tool=r.getOrDefault("tool","");
        if (!(mode.equals("actor")?ACTOR_TOOLS:OPERATOR_TOOLS).contains(tool)) throw new Denied("TOOL_NOT_ALLOWED");
        Set<String> keys=switch(tool) {
            case "init" -> Set.of("tool","employee_id","event_id","event_sequence","effective_at","enabled","sessions","grants","asset_id","asset_outage");
            case "inspect_employee" -> Set.of("tool","employee_id");
            case "read_policy" -> Set.of("tool","policy_id");
            case "propose_plan" -> Set.of("tool","employee_id","intent");
            case "execute_step" -> Set.of("tool","workflow_id","step_id");
            case "approve" -> Set.of("tool","workflow_id","digest","approver");
            case "request_handoff","stop_actor" -> Set.of("tool","workflow_id","reason_code");
            case "begin_turn" -> Set.of("tool");
            case "charge_wait" -> Set.of("tool","milliseconds");
            case "import_event" -> Set.of("tool","employee_id","event_id","event_sequence","effective_at","intent","role");
            case "advance_clock" -> Set.of("tool","workflow_id","seconds");
            default -> Set.of("tool","workflow_id");
        };
        if (tool.equals("init")) {
            var extras=Set.of("intent","role","account_exists","inventory_id","inventory_available","failure_step","cleanup_failure","turn_limit","receipt_unavailable","initial_version");
            if (!r.keySet().containsAll(keys) || r.keySet().stream().anyMatch(k->!keys.contains(k)&&!extras.contains(k))) throw new Denied("INVALID_ARGUMENTS");
            return initialize(r);
        }
        if (!r.keySet().equals(keys)) throw new Denied("INVALID_ARGUMENTS");
        if (!workflows.exists()) throw new Denied("NOT_INITIALIZED");
        var s=workflows.read();
        if (r.containsKey("employee_id")&&!r.get("employee_id").equals(s.get("employee_id"))) throw new Denied("EMPLOYEE_SCOPE_DENIED");
        if (r.containsKey("workflow_id")&&!r.get("workflow_id").equals(s.get("workflow_id"))) throw new Denied("WORKFLOW_SCOPE_DENIED");
        if (tool.equals("begin_turn")) {
            try { chargeTurn(true); return status(); }
            catch (Denied denied) { var result=status(); result.put("code",denied.code); return result; }
        }
        if (tool.equals("charge_wait")) {
            if (!r.get("milliseconds").matches("[0-9]{1,4}") || Integer.parseInt(r.get("milliseconds"))>2000) throw new Denied("INVALID_ARGUMENTS");
            long reserved=Long.parseLong(s.get("active_reserved_ms"))+Integer.parseInt(r.get("milliseconds"));
            if (reserved>120000) { safetyStop("ACTOR_BUDGET_EXHAUSTED"); throw new Denied("ACTOR_BUDGET_EXHAUSTED"); }
            s.put("active_reserved_ms",Long.toString(reserved)); workflows.save(s); return status();
        }
        if (mode.equals("actor")&&!tool.equals("stop_actor")) chargeTool();
        return switch(tool) {
            case "inspect_employee" -> inspect();
            case "read_policy" -> policy(r.get("policy_id"));
            case "propose_plan" -> propose(r.get("intent"));
            case "review" -> review();
            case "approve" -> approve(r.get("digest"),r.get("approver"));
            case "execute_step" -> execute(r.get("step_id"));
            case "verify_outcome" -> verify();
            case "request_handoff","stop_actor" -> {
                String reason=r.get("reason_code");
                if (!Set.of("ACTOR_STOPPED","INVALID_PROVIDER_OUTPUT","ACTOR_BUDGET_EXHAUSTED","PROVIDER_FAILURE","PROVIDER_TIMEOUT","OPERATOR_REVIEW").contains(reason)) throw new Denied("INVALID_REASON");
                safetyStop(reason); yield status();
            }
            case "cancel" -> { safetyStop("CANCELLED"); yield status(); }
            case "import_event" -> importEvent(r);
            case "activate_event" -> {
                var previous=workflows.read();
                if(sameEvent(previous)||!previous.get("administrative_status").equals("SUPERSEDED")) throw new Denied("PREVIOUS_WORKFLOW_UNRESOLVED");
                workflows.save(fresh(hrStore.read(),previous)); yield status();
            }
            case "advance_clock" -> {
                if (!r.get("seconds").matches("[0-9]{1,8}")) throw new Denied("INVALID_CLOCK");
                var current=workflows.read();
                long offset=Math.addExact(Long.parseLong(current.get("clock_offset_seconds")),Long.parseLong(r.get("seconds")));
                if (offset>31536000) throw new Denied("INVALID_CLOCK");
                current.put("clock_offset_seconds",Long.toString(offset)); workflows.save(current); yield status();
            }
            default -> status();
        };
    }
    private Instant now() { return clock.instant().plusSeconds(Long.parseLong(workflows.read().getOrDefault("clock_offset_seconds","0"))); }
    private static boolean done(Map<String,String> s,String a) { return s.getOrDefault("step."+a,"PENDING").equals("DONE"); }
    private static List<String> forward(Map<String,String> s) { return s.get("intent").equals("onboard")?JOIN:STEPS; }
    private static List<String> allSteps() { return java.util.stream.Stream.of(STEPS,JOIN,CLEANUP).flatMap(List::stream).toList(); }
    private static String normalizeGrants(String input) throws Denied {
        if (input.isEmpty()) return "";
        String[] grants=input.split(",",-1);
        if (grants.length>16 || Arrays.stream(grants).anyMatch(g->!g.matches("[a-z][a-z0-9_-]{0,31}")) || Arrays.stream(grants).distinct().count()!=grants.length) throw new Denied("INVALID_GRANTS");
        Arrays.sort(grants); return String.join(",",grants);
    }
    private Map<String,String> fresh(Map<String,String> hr,Map<String,String> prior) {
        var s=new HashMap<String,String>();
        s.put("workflow_id","wf-"+hr.get("employee_id").replace("-","")+"-"+hr.get("event_sequence"));
        for (String k:List.of("employee_id","intent","role","event_id","event_sequence","epoch")) s.put(k,hr.get(k));
        s.put("administrative_status","RECEIVED"); s.put("digest",""); s.put("reason","");
        for (String k:List.of("actor_calls","provider_turns","active_reserved_ms","safety_calls")) s.put(k,"0");
        s.put("provider_pending","false"); s.put("actor_session","false");
        s.put("clock_offset_seconds",prior.getOrDefault("clock_offset_seconds","0")); s.put("turn_limit",prior.getOrDefault("turn_limit","24"));
        s.put("fault.receipt_unavailable",prior.getOrDefault("fault.receipt_unavailable","false"));
        for (String f:List.of("asset_outage","failure_step","cleanup_failure")) s.put("fault."+f,prior.getOrDefault("fault."+f,f.equals("asset_outage")?"false":""));
        for (String a:allSteps()) { s.put("step."+a,"PENDING"); s.put("attempts."+a,"0"); s.put("due."+a,"0"); }
        return s;
    }
    private Map<String,String> initialize(Map<String,String> r) throws Exception {
        if (workflows.exists()) throw new Denied("ALREADY_INITIALIZED");
        String employee=r.get("employee_id"), intent=r.getOrDefault("intent","offboard"), role=r.getOrDefault("role","engineer");
        validateEvent(r); normalizeGrants(r.get("grants"));
        if (!employee.matches("E-[0-9]{1,8}") || !Set.of("onboard","offboard").contains(intent) || !BUNDLES.containsKey(role)
            || !r.get("sessions").matches("[0-9]{1,6}") || !r.get("asset_id").matches("[A-Za-z0-9_-]{0,64}")
            || !r.getOrDefault("inventory_id","LAP-POOL").matches("[A-Za-z0-9_-]{1,64}") || !r.getOrDefault("turn_limit","24").matches("[1-9]|1[0-9]|2[0-4]")) throw new Denied("INVALID_SEED");
        for (String k:List.of("enabled","asset_outage","account_exists","inventory_available","receipt_unavailable")) if (!Set.of("true","false").contains(r.getOrDefault(k,"true"))) throw new Denied("INVALID_SEED");
        if (!r.getOrDefault("initial_version","1").matches("[1-9][0-9]{0,2}")) throw new Denied("INVALID_SEED");
        if (!r.getOrDefault("failure_step","").isEmpty()&&!forward(Map.of("intent",intent)).contains(r.get("failure_step"))) throw new Denied("INVALID_SEED");
        if (!r.getOrDefault("cleanup_failure","").isEmpty()&&!CLEANUP.contains(r.get("cleanup_failure"))) throw new Denied("INVALID_SEED");
        String exists=r.getOrDefault("account_exists","true");
        if (exists.equals("false")&&(r.get("enabled").equals("true")||!r.get("sessions").equals("0")||!r.get("grants").isEmpty())) throw new Denied("INVALID_SEED");
        var hr=Services.seed(employee,"event_id",r.get("event_id"),"event_sequence",r.get("event_sequence"),"epoch","1","intent",intent,"role",role,"effective_at",r.get("effective_at"),"administrative_status","ACTIVE","event_count","1");
        hr.put("event."+r.get("event_sequence"),r.get("event_id")+":"+eventHash(hr));
        var identity=Services.seed(employee,"enabled",r.get("enabled"),"sessions",r.get("sessions"),"grants",normalizeGrants(r.get("grants")),"account_exists",exists,
            "account_state",exists.equals("true")?(r.get("enabled").equals("true")?"ACTIVE":"INACTIVE"):"MISSING","created_by","","enabled_by","","grants_added_by","","added_grants","");
        var assets=Services.seed(employee,"asset_id",r.get("asset_id"),"collection_task","","collection_status","NONE","inventory_id",r.getOrDefault("inventory_id","LAP-POOL"),"inventory_available",r.getOrDefault("inventory_available","true"),"reserved_by","");
        var options=new HashMap<String,String>(); options.put("turn_limit",r.getOrDefault("turn_limit","24"));
        options.put("fault.receipt_unavailable",r.getOrDefault("receipt_unavailable","false"));
        for (String k:List.of("asset_outage","failure_step","cleanup_failure")) if (r.containsKey(k)) options.put("fault."+k,r.get(k));
        for (var record:List.of(hr,identity,assets)) record.put("version",r.getOrDefault("initial_version","1"));
        hrStore.save(hr); identityStore.save(identity); assetStore.save(assets); workflows.save(fresh(hr,options)); return status();
    }
    private static void validateEvent(Map<String,String> r) throws Exception {
        if (!r.get("event_id").matches("[A-Za-z0-9_-]{1,64}")||!r.get("event_sequence").matches("[1-9][0-9]{0,8}")) throw new Denied("INVALID_EVENT");
        Instant.parse(r.get("effective_at"));
    }
    private static String eventHash(Map<String,String> r) throws Exception {
        var fields=new TreeMap<String,String>();
        for (String k:List.of("employee_id","event_id","event_sequence","effective_at","intent","role")) fields.put(k,r.get(k)); return digest(fields);
    }
    private Map<String,String> importEvent(Map<String,String> r) throws Exception {
        validateEvent(r);
        if (!Set.of("onboard","offboard").contains(r.get("intent"))||!BUNDLES.containsKey(r.get("role"))) throw new Denied("INVALID_EVENT");
        var hr=hrStore.read(); String hash=eventHash(r);
        String old=hr.entrySet().stream().filter(e->e.getKey().startsWith("event.")&&e.getValue().startsWith(r.get("event_id")+":"))
                .map(Map.Entry::getValue).findFirst().orElse(null);
        if (old!=null) { if (!old.equals(r.get("event_id")+":"+hash)) throw new Denied("EVENT_REPLAY_CONFLICT"); return status(); }
        if (Long.parseLong(r.get("event_sequence"))<=Long.parseLong(hr.get("event_sequence"))) throw new Denied("OLDER_EVENT_DENIED");
        if (Integer.parseInt(hr.get("event_count"))>=16) throw new Denied("EVENT_BUDGET_EXHAUSTED");
        if (r.get("intent").equals("onboard")&&hr.get("intent").equals("offboard")) throw new Denied("REHIRE_REQUIRES_REVIEW");
        for (String k:List.of("event_id","event_sequence","effective_at","intent","role")) hr.put(k,r.get(k));
        hr.put("epoch",Long.toString(Long.parseLong(hr.get("epoch"))+1)); hr.put("version",Long.toString(Long.parseLong(hr.get("version"))+1));
        hr.put("event_count",Integer.toString(Integer.parseInt(hr.get("event_count"))+1)); hr.put("event."+r.get("event_sequence"),r.get("event_id")+":"+hash); hr.put("administrative_status","ACTIVE");
        hr.put("commit_order",Long.toString(nextOrder()));
        hrStore.save(hr); // commit authority first; restart fences the predecessor
        safetyStop("SUPERSEDED"); return status();
    }
    private void chargeTurn(boolean session) throws Exception {
        var s=workflows.read();
        if (Integer.parseInt(s.get("provider_turns"))>=Integer.parseInt(s.get("turn_limit"))||Long.parseLong(s.get("active_reserved_ms"))+7000>120000) {
            safetyStop("ACTOR_BUDGET_EXHAUSTED"); throw new Denied("ACTOR_BUDGET_EXHAUSTED");
        }
        s.put("provider_turns",Integer.toString(Integer.parseInt(s.get("provider_turns"))+1)); s.put("active_reserved_ms",Long.toString(Long.parseLong(s.get("active_reserved_ms"))+7000));
        s.put("provider_pending","true"); if (session) s.put("actor_session","true"); workflows.save(s);
    }
    private void chargeTool() throws Exception {
        var s=workflows.read();
        if (Integer.parseInt(s.get("actor_calls"))>=32) { safetyStop("ACTOR_BUDGET_EXHAUSTED"); throw new Denied("ACTOR_BUDGET_EXHAUSTED"); }
        if (!s.get("provider_pending").equals("true")) { chargeTurn(false); s=workflows.read(); }
        s.put("provider_pending","false"); s.put("actor_calls",Integer.toString(Integer.parseInt(s.get("actor_calls"))+1)); workflows.save(s);
    }
    void actorDisconnected() throws Exception {
        if (workflows.exists()&&workflows.read().get("actor_session").equals("true")) safetyStop("ACTOR_STOPPED");
    }
    private Map<String,String> inspect() {
        var hr=hrStore.read(); var i=identityStore.read(); var a=assetStore.read(); var r=new HashMap<String,String>(); r.put("code","OK");
        for (String k:List.of("employee_id","event_id","intent","role","event_sequence","epoch","effective_at")) r.put(k,hr.get(k));
        for (String k:List.of("enabled","sessions","grants","account_exists")) r.put(k,i.get(k));
        r.put("asset_id",a.get("asset_id")); r.put("hr_version",hr.get("version")); r.put("identity_version",i.get("version")); r.put("assets_version",a.get("version")); return r;
    }
    private Map<String,String> policy(String id) throws Denied {
        if (!Set.of("offboarding-v1","onboarding-v1").contains(id)) throw new Denied("UNKNOWN_POLICY");
        return Map.of("code","OK","policy_id",id,"policy_version","1","required_steps",String.join(",",id.equals("onboarding-v1")?JOIN:STEPS),"role_engineer",BUNDLES.get("engineer"),"role_support",BUNDLES.get("support"),"approval_required","true");
    }
    private Map<String,String> propose(String intent) throws Exception {
        var s=workflows.read(); var hr=hrStore.read();
        if (!Set.of("onboard","offboard").contains(intent)||!hr.get("intent").equals(intent)) throw new Denied("INTENT_MISMATCH");
        if (!sameEvent(s)) { if (!s.get("administrative_status").equals("SUPERSEDED")) throw new Denied("PREVIOUS_WORKFLOW_UNRESOLVED"); s=fresh(hr,s); }
        if (!s.get("digest").isEmpty()) return status();
        var facts=inspect();
        if (intent.equals("onboard")&&(!facts.get("enabled").equals("false")||!facts.get("sessions").equals("0")||!facts.get("asset_id").isEmpty()
            || !Set.of(BUNDLES.get(s.get("role")).split(",")).containsAll(facts.get("grants").isEmpty()?Set.of():Set.of(facts.get("grants").split(","))))) throw new Denied("ONBOARD_PRECONDITION_DENIED");
        for (String k:List.of("event_id","event_sequence","epoch","effective_at","role","hr_version","identity_version","assets_version","grants","asset_id","account_exists","enabled","sessions")) s.put("approved."+k,facts.get(k));
        s.put("approved.inventory_id",assetStore.read().get("inventory_id")); s.put("approved.inventory_available",assetStore.read().get("inventory_available"));
        s.put("approved.target_grants",intent.equals("onboard")?BUNDLES.get(s.get("role")):"");
        for (String name:List.of("hr","identity","assets")) s.put("expected."+name,facts.get(name+"_version"));
        s.put("digest",digest(planFields(s))); s.put("administrative_status","AWAITING_APPROVAL"); workflows.save(s); return status();
    }
    private Map<String,String> planFields(Map<String,String> s) {
        var p=new TreeMap<String,String>();
        for (String k:List.of("workflow_id","employee_id","intent","role","epoch")) p.put(k,s.get(k));
        p.put("policy_id",s.get("intent").equals("onboard")?"onboarding-v1":"offboarding-v1"); p.put("policy_version","1"); p.put("steps",String.join(",",forward(s)));
        p.put("compensation",s.get("intent").equals("onboard")?String.join(",",CLEANUP)+":owned_only":"disable_login,revoke_sessions,remove_grants:never_restore_access");
        s.forEach((k,v)->{if(k.startsWith("approved.")) p.put(k,v);}); return p;
    }
    private static String digest(Map<String,String> fields) throws Exception {
        var bytes=new ByteArrayOutputStream(); var data=new DataOutputStream(bytes);
        for (var e:new TreeMap<>(fields).entrySet()) for(String v:List.of(e.getKey(),e.getValue())) { byte[] encoded=v.getBytes(StandardCharsets.UTF_8); data.writeInt(encoded.length); data.write(encoded); }
        return java.util.HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes.toByteArray()));
    }
    private Map<String,String> review() throws Denied {
        var s=workflows.read(); if(s.get("digest").isEmpty()) throw new Denied("NO_PLAN");
        var p=planFields(s); p.put("code","OK"); p.put("digest",s.get("digest")); p.put("approver_required","hr-reviewer"); return p;
    }
    private Map<String,String> approve(String hash,String approver) throws Exception {
        var s=workflows.read();
        if(!s.get("administrative_status").equals("AWAITING_APPROVAL")) throw new Denied("NOT_AWAITING_APPROVAL");
        if(!approver.equals("hr-reviewer")) throw new Denied("APPROVER_DENIED");
        if(!hash.equals(s.get("digest"))||hash.isEmpty()||!hash.equals(digest(planFields(s)))) throw new Denied("APPROVAL_DIGEST_MISMATCH");
        checkVersions(s); s.put("approval_digest",hash); s.put("approval_approver",approver); s.put("approval_expires",now().plusSeconds(86400).toString()); s.put("administrative_status","RUNNING"); workflows.save(s); return status();
    }
    private boolean sameEvent(Map<String,String> s) {
        var hr=hrStore.read(); return List.of("event_id","event_sequence","epoch","intent","role").stream().allMatch(k->hr.get(k).equals(s.get(k)));
    }
    private void checkVersions(Map<String,String> s) throws Exception {
        if(!sameEvent(s)||!hrStore.read().get("effective_at").equals(s.get("approved.effective_at"))) throw new Denied("STALE_APPROVAL");
        for(String name:List.of("hr","identity","assets")) if(!storeFor(name).read().get("version").equals(s.get("expected."+name))) throw new Denied("STALE_APPROVAL");
        if(!assetStore.read().get("asset_id").equals(done(s,"reserve_asset")?s.get("approved.inventory_id"):s.get("approved.asset_id"))) throw new Denied("STALE_APPROVAL");
    }
    private void checkApproval(Map<String,String> s) throws Exception {
        if(!s.containsKey("approval_digest")||!s.get("approval_digest").equals(s.get("digest"))||!s.get("digest").equals(digest(planFields(s)))) throw new Denied("APPROVAL_REQUIRED");
        if(!now().isBefore(Instant.parse(s.get("approval_expires")))) throw new Denied("APPROVAL_EXPIRED");
        if(now().isBefore(Instant.parse(s.get("approved.effective_at")))) throw new Denied("NOT_EFFECTIVE");
        checkVersions(s);
    }
    private static String serviceFor(String step) {
        return switch(step) {
            case "disable_login","revoke_sessions","remove_grants","prepare_account","add_role_grants","enable_login","compensate_account","undo_role_grants" -> "identity";
            case "create_collection_task","reserve_asset","release_asset" -> "assets";
            default -> "hr";
        };
    }
    private SnapshotStore storeFor(String name) { return switch(name) { case "identity"->identityStore; case "assets"->assetStore; default->hrStore; }; }
    private String operationKey(Map<String,String> s,String a) { return s.get("workflow_id")+"/"+s.get("epoch")+"/"+a; }
    private String operationHash(Map<String,String> s,String a) throws Exception { return digest(Map.of("digest",s.get("digest"),"step",a)); }
    private void reconcile() throws Exception {
        var s=workflows.read(); boolean changed=false;
        for(String a:allSteps()) {
            if(!s.get("step."+a).equals("INTENT")) continue;
            if(s.get("fault.receipt_unavailable").equals("true")) {
                s.put("administrative_status","RECOVERY_BLOCKED"); s.put("reason","RECEIPT_LOOKUP_UNAVAILABLE"); workflows.save(s); return;
            }
            String name=serviceFor(a); var record=storeFor(name).read(); String receipt=record.get(Services.ledgerKey(operationKey(s,a),a));
            if(receipt==null) s.put("step."+a,"PENDING");
            else {
                if(!receipt.equals(operationKey(s,a)+":"+operationHash(s,a))||Long.parseLong(record.get("version"))!=Long.parseLong(s.get("expected."+name))+1) throw new IllegalStateException("In-flight receipt conflict");
                s.put("step."+a,"DONE"); s.put("expected."+name,record.get("version")); s.put("recovered_receipt",a);
            }
            changed=true;
        }
        if(changed) workflows.save(s);
    }
    private void crash(String phase,String a) throws Exception {
        String hook="disable_login".equals(crashAfter)?"after_service_commit:disable_login":crashAfter;
        if(!(phase+":"+a).equals(hook)) return;
        Path marker=runDirectory.resolve("crash-fired.marker");
        if(!Files.exists(marker)) { Files.writeString(marker,phase+":"+a+"\n",java.nio.file.StandardOpenOption.CREATE_NEW); Runtime.getRuntime().halt(91); }
    }
    private boolean applyStep(String a,boolean safety) throws Exception {
        var s=workflows.read(); String name=serviceFor(a); int attempts=Integer.parseInt(s.get("attempts."+a));
        if(attempts>=3||(safety&&Integer.parseInt(s.get("safety_calls"))>=12)) return false;
        crash("before_intent",a); s.put("step."+a,"INTENT"); s.put("attempts."+a,Integer.toString(attempts+1));
        if(safety) s.put("safety_calls",Integer.toString(Integer.parseInt(s.get("safety_calls"))+1));
        workflows.save(s); crash("after_intent",a);
        boolean fault=s.get("fault."+(safety?"cleanup_failure":"failure_step")).equals(a)||(!safety&&Set.of("reserve_asset","create_collection_task").contains(a)&&s.get("fault.asset_outage").equals("true"));
        if(fault) { s.put("step."+a,"PENDING"); s.put("due."+a,Long.toString(now().toEpochMilli()+(attempts+1)*1000L)); workflows.save(s); return false; }
        Services.Service service=switch(name) {
            case "identity"->new Services.Identity(identityStore,s.get("approved.grants"),s.get("approved.target_grants"));
            case "assets"->new Services.Assets(assetStore);
            default->new Services.Hr(hrStore);
        };
        if (!safety && !sameEvent(s)) throw new Denied("STALE_APPROVAL");
        var authority=hrStore.read(); authority.put("commit_order",Long.toString(nextOrder()));
        authority.put("commit_time",now().toString()); authority.put("execution_mode",safety?"safety":"forward");
        var receipt=service.apply(a,operationKey(s,a),operationHash(s,a),Long.parseLong(s.get("expected."+name)),authority);
        crash("after_service_commit",a); s.put("step."+a,"DONE"); s.put("expected."+name,Long.toString(receipt.version())); s.put("due."+a,"0"); workflows.save(s); crash("after_result",a); return true;
    }
    private Map<String,String> execute(String a) throws Exception {
        var s=workflows.read();
        if(!forward(s).contains(a)) throw new Denied("UNKNOWN_STEP");
        try { checkApproval(s); } catch(Denied d) {
            if(Set.of("STALE_APPROVAL","APPROVAL_EXPIRED").contains(d.code)) {
                if(s.get("intent").equals("onboard")) safetyStop(d.code);
                else { s.put("administrative_status","STALE_APPROVAL"); s.put("reason",d.code); workflows.save(s); }
            }
            throw d;
        }
        if(done(s,a)) return status();
        if(!RUNNING.contains(s.get("administrative_status"))) throw new Denied("WORKFLOW_NOT_RUNNING");
        final var before=s;
        if(!forward(s).stream().filter(k->!done(before,k)).findFirst().orElse("").equals(a)) throw new Denied("STEP_PREREQUISITE_DENIED");
        if(now().toEpochMilli()<Long.parseLong(s.get("due."+a))) throw new Denied("RETRY_NOT_DUE");
        if(a.equals("complete_hr")&&!accessRevoked()) throw new Denied("INCOMPLETE_REVOCATION");
        boolean applied;
        try { applied=applyStep(a,false); } catch(Denied d) {
            var failed=workflows.read(); failed.put("step."+a,"PENDING"); workflows.save(failed); safetyStop(d.code); throw d;
        }
        s=workflows.read();
        if(!applied) {
            boolean exhausted=Integer.parseInt(s.get("attempts."+a))>=3;
            s.put("reason",Set.of("reserve_asset","create_collection_task").contains(a)?"ASSET_SERVICE_UNAVAILABLE":"SERVICE_UNAVAILABLE"); s.put("administrative_status",exhausted?"BLOCKED":"RETRY_PENDING"); workflows.save(s);
            if(exhausted&&s.get("intent").equals("onboard")) safetyStop("SERVICE_UNAVAILABLE");
            var result=status(); result.put("code","TRANSIENT"); return result;
        }
        s.put("administrative_status","RUNNING"); s.put("reason",""); workflows.save(s);
        return a.equals("complete_hr")||a.equals("complete_onboarding_hr")?verify():status();
    }
    private void safetyStop(String reason) throws Exception {
        var s=workflows.read(); String admin=s.get("administrative_status");
        if(Set.of("COMPENSATING","SAFETY_REVOKING").contains(admin)) { runSafety(); return; }
        if(reason.equals("SUPERSEDED")&&admin.equals("SUPERSEDED")) return;
        s.put("actor_session","false"); s.put("provider_pending","false");
        if(reason.equals("CANCELLED")&&!s.containsKey("approval_digest")) {
            s.put("administrative_status","CANCELLED"); s.put("reason",reason); workflows.save(s); return;
        }
        if(!reason.equals("SUPERSEDED")&&!reason.equals("SERVICE_UNAVAILABLE")&&!RUNNING.contains(admin)) { workflows.save(s); return; }
        s.put("safety_reason",reason); s.put("reason",reason);
        if(!s.containsKey("approval_digest")||admin.equals("COMPLETED")) { s.put("administrative_status",reason.equals("SUPERSEDED")?"SUPERSEDED":"CANCELLED"); workflows.save(s); return; }
        if(!s.get("approval_digest").equals(s.get("digest"))||!s.get("digest").equals(digest(planFields(s)))) throw new Denied("APPROVAL_REQUIRED");
        if(now().isBefore(Instant.parse(s.get("approved.effective_at")))) {
            if(reason.equals("CANCELLED")) s.put("administrative_status","CANCELLED");
            else if(reason.equals("SUPERSEDED")) s.put("administrative_status","SUPERSEDED");
            workflows.save(s); return;
        }
        if(s.get("intent").equals("offboard")&&reason.equals("SUPERSEDED")) { s.put("administrative_status","SUPERSEDED"); workflows.save(s); return; }
        s.put("administrative_status",s.get("intent").equals("onboard")?"COMPENSATING":"SAFETY_REVOKING"); workflows.save(s); runSafety();
    }
    private void runSafety() throws Exception {
        var initial=workflows.read(); List<String> actions=initial.get("intent").equals("onboard")?CLEANUP:STEPS.subList(0,3);
        for(String a:actions) {
            var s=workflows.read(); if(done(s,a)) continue;
            if(a.equals("fail_onboarding_hr")&&!sameEvent(s)) continue;
            if(s.get("intent").equals("offboard")&&!sameEvent(s)) { blockSafety("STALE_APPROVAL"); return; }
            if(!storeFor(serviceFor(a)).read().get("version").equals(s.get("expected."+serviceFor(a)))) { blockSafety("STALE_APPROVAL"); return; }
            while(!done(workflows.read(),a)&&Integer.parseInt(workflows.read().get("attempts."+a))<3) {
                long wait=Long.parseLong(workflows.read().get("due."+a))-now().toEpochMilli();
                if(wait>0) Thread.sleep(Math.min(wait,2000));
                try { if(applyStep(a,true)) break; } catch(Denied d) { blockSafety(d.code); return; }
            }
            if(!done(workflows.read(),a)) { blockSafety("CLEANUP_SERVICE_UNAVAILABLE"); return; }
        }
        var s=workflows.read(); String reason=s.get("safety_reason");
        s.put("administrative_status",reason.equals("SUPERSEDED")?"SUPERSEDED":s.get("intent").equals("onboard")?"COMPENSATED":reason.equals("CANCELLED")?"CANCELLED":"HANDOFF"); s.put("reason",reason); workflows.save(s);
    }
    private void blockSafety(String reason) throws Exception { var s=workflows.read(); s.put("administrative_status","BLOCKED_COMPENSATION"); s.put("reason",reason); workflows.save(s); }
    private long nextOrder() {
        return List.of(hrStore,identityStore,assetStore).stream().mapToLong(store->Long.parseLong(store.read().get("commit_order"))).max().orElseThrow()+1;
    }
    private boolean accessRevoked() { var i=identityStore.read(); return i.get("enabled").equals("false")&&i.get("sessions").equals("0")&&i.get("grants").isEmpty(); }
    private Map<String,String> verify() throws Exception {
        var s=workflows.read(); var i=identityStore.read(); var a=assetStore.read();
        if(!RUNNING.contains(s.get("administrative_status"))&&!s.get("administrative_status").equals("COMPLETED")) return status();
        boolean complete=forward(s).stream().allMatch(k->done(s,k));
        boolean valid=s.get("intent").equals("onboard")?i.get("enabled").equals("true")&&i.get("grants").equals(s.get("approved.target_grants"))&&a.get("asset_id").equals(s.get("approved.inventory_id"))&&hrStore.read().get("administrative_status").equals("ONBOARDED")
            :accessRevoked()&&(a.get("asset_id").isEmpty()||(!a.get("collection_task").isEmpty()&&a.get("collection_status").equals("OPEN")))&&hrStore.read().get("administrative_status").equals("OFFBOARDED");
        if(complete&&valid&&sameEvent(s)) { s.put("administrative_status","COMPLETED"); workflows.save(s); }
        else if(complete) { s.put("administrative_status","BLOCKED"); s.put("reason","VERIFICATION_FAILED"); workflows.save(s); }
        return status();
    }
    private Map<String,String> status() {
        var s=workflows.read(); var a=assetStore.read(); var r=new HashMap<String,String>(); r.put("code","OK");
        for(String k:List.of("workflow_id","employee_id","digest","intent","role","reason","actor_calls","provider_turns","active_reserved_ms","safety_calls")) r.put(k,s.get(k));
        String admin=s.get("administrative_status");
        if(RUNNING.contains(admin)&&now().isBefore(Instant.parse(s.get("approved.effective_at")))) admin="WAITING_EFFECTIVE_TIME";
        r.put("administrative_status",admin); r.put("access_status",accessRevoked()?"REVOKED":identityStore.read().get("enabled").equals("true")?"ACTIVE":"DISABLED");
        for(String k:List.of("collection_task","collection_status")) r.put(k,a.get(k)); r.put("physical_return_verified","false");
        List<String> steps=Set.of("BLOCKED_COMPENSATION","COMPENSATING").contains(admin)?CLEANUP:forward(s);
        String outstanding=steps.stream().filter(k->!done(s,k)).findFirst().orElse("");
        r.put("outstanding_step",outstanding); r.put("responsible_role",serviceFor(outstanding).equals("assets")?"asset_operator":"hr-reviewer");
        r.put("completed_steps",Long.toString(forward(s).stream().filter(k->done(s,k)).count())); r.put("eligible_step",""); r.put("retry_after_ms","0");
        if(RUNNING.contains(admin)&&!outstanding.isEmpty()) { long wait=Math.max(0,Long.parseLong(s.get("due."+outstanding))-now().toEpochMilli()); if(wait==0) r.put("eligible_step",outstanding); else r.put("retry_after_ms",Long.toString(wait)); }
        r.put("recovered_receipt",s.getOrDefault("recovered_receipt","")); return r;
    }
    private void validateCommittedState() throws Exception {
        var s=workflows.read();
        if(!s.keySet().containsAll(Set.of("workflow_id","employee_id","administrative_status","actor_calls","digest","reason","intent","role","epoch","provider_turns","active_reserved_ms","safety_calls","clock_offset_seconds","turn_limit","actor_session","provider_pending"))) throw new IllegalStateException("Incomplete workflow snapshot");
        if(!BUNDLES.containsKey(s.get("role"))||!Set.of("onboard","offboard").contains(s.get("intent"))) throw new IllegalStateException("Invalid workflow intent");
        for(String k:List.of("actor_calls","provider_turns","active_reserved_ms","safety_calls","clock_offset_seconds","turn_limit")) if(Long.parseLong(s.get(k))<0) throw new IllegalStateException("Invalid persisted budget");
        if(Integer.parseInt(s.get("actor_calls"))>32||Integer.parseInt(s.get("provider_turns"))>24||Long.parseLong(s.get("active_reserved_ms"))>120000||Integer.parseInt(s.get("safety_calls"))>12) throw new IllegalStateException("Exceeded persisted budget");
        for(var store:List.of(hrStore,identityStore,assetStore)) if(!store.read().get("employee_id").equals(s.get("employee_id"))||Long.parseLong(store.read().get("version"))<1) throw new IllegalStateException("Invalid service snapshot");
        for(String k:allSteps()) { if(!Set.of("PENDING","INTENT","DONE").contains(s.get("step."+k))||Integer.parseInt(s.get("attempts."+k))<0||Integer.parseInt(s.get("attempts."+k))>3) throw new IllegalStateException("Invalid step snapshot"); Long.parseLong(s.get("due."+k)); }
        if(!Set.of("true","false").contains(identityStore.read().get("enabled"))||Integer.parseInt(identityStore.read().get("sessions"))<0) throw new IllegalStateException("Invalid identity snapshot");
        normalizeGrants(identityStore.read().get("grants")); Instant.parse(hrStore.read().get("effective_at"));
    }
}

