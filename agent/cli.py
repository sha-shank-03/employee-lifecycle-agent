"""Local offboarding CLI. Operator approvals are separate from agent tool access."""
import argparse
import json
from pathlib import Path
import sys
from .bridge import BridgeError, JavaBridge, ROOT
from .loop import run_loop
from .protocol import strict_json
from .providers import provider_for


def read_json(path):
    raw = Path(path).read_text(encoding="utf-8")
    if len(raw.encode("utf-8")) > 16_384:
        raise ValueError("JSON input exceeds 16 KiB")
    return strict_json(raw)


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def operator(run_dir, tool, **arguments):
    with JavaBridge(run_dir, mode="operator") as bridge:
        result = bridge.request({"tool": tool, **arguments})
    if result["code"] != "OK":
        raise RuntimeError(result["code"])
    return result


def initialize(fixture, run_dir):
    run_dir = Path(run_dir)
    if run_dir.exists() and any(run_dir.iterdir()):
        raise ValueError("run directory must be empty; use resume for an existing run")
    seed = read_json(Path(fixture) / "seed.json")
    result = operator(run_dir, "init", **{key: str(value).lower() if type(value) is bool else str(value) for key, value in seed.items()})
    write_json(run_dir / "request.json", read_json(Path(fixture) / "request.json"))
    return result


def validate_request(request):
    if set(request) != {"employee_id", "intent", "text"} or any(type(v) is not str for v in request.values()):
        raise ValueError("request requires employee_id, intent and text strings only")
    if request["intent"] not in {"offboard", "onboard"} or len(request["text"].encode("utf-8")) > 16_384:
        raise ValueError("explicit bounded onboarding/offboarding intent required")


def act(run_dir, request, *, crash_after=None, provider="scripted"):
    validate_request(request)
    with JavaBridge(run_dir, mode="actor", crash_after=crash_after) as bridge:
        instance = provider_for(provider) if isinstance(provider, str) else provider
        transcript = run_loop(instance, bridge, request)
    if hasattr(instance, "trace"):
        transcript["provider_protocol_trace"] = instance.trace
        transcript["synthetic_replay"] = getattr(instance, "mode", "") == "synthetic-replay"
    # Trace writing is harness-owned; the actor has no filesystem tool.
    traces = Path(run_dir) / "traces"
    traces.mkdir(exist_ok=True)
    write_json(traces / f"turn-{len(list(traces.glob('turn-*.json'))) + 1:03d}.json", transcript)
    # An operator report supplies authority; a final draft does not mark success.
    workflow = transcript["workflow_id"] or next((o["result"]["workflow_id"] for o in reversed(transcript["observations"]) if "workflow_id" in o["result"]), "")
    if not workflow:
        raise RuntimeError("No valid workflow obtained; inspect request and domain state")
    return operator(run_dir, "report", workflow_id=workflow)


def create_review(run_dir, workflow):
    packet = operator(run_dir, "review", workflow_id=workflow)
    path = Path(run_dir) / "review" / f"{workflow}.json"
    write_json(path, packet)
    return packet, path


def approve_review(run_dir, workflow, review_file, approver):
    packet = read_json(review_file)
    if packet.get("workflow_id") != workflow or type(packet.get("digest")) is not str:
        raise ValueError("review file does not match workflow")
    return operator(run_dir, "approve", workflow_id=workflow, digest=packet["digest"], approver=approver)


def demo(scenario, run_dir, provider="scripted"):
    fixture = ROOT / "fixtures" / "dev" / scenario
    if not fixture.is_dir():
        raise ValueError("unknown development scenario")
    print("Fictional local demo; provider decisions and operator approvals are SCRIPTED.")
    print("Creating a collection task does not verify physical asset return.")
    from evaluation.scenarios import run_case
    result = run_case(read_json(fixture / "seed.json"), read_json(fixture / "request.json"),
                      read_json(fixture / "driver.json"), run_dir, provider)
    from evaluation.verifier import verify_run
    verification = verify_run(run_dir, read_json(fixture / "expected.json"))
    write_json(Path(run_dir) / "outcome.json", {"domain": result, "verification": verification,
               "provider": provider, "live_model_evaluation": False})
    print(json.dumps({"domain": result, "verification": verification}, indent=2))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "submit", "resume", "review", "approve", "report", "cancel", "import-event", "activate-event", "advance-clock", "demo"):
        sub = commands.add_parser(name)
        sub.add_argument("--run-dir", required=True)
        if name == "init": sub.add_argument("--fixture", required=True)
        if name == "submit": sub.add_argument("--request", required=True)
        if name in {"submit", "resume", "demo"}:
            choices = ["scripted", "scripted-adaptive", "fixed"] + ([] if name == "demo" else ["responses", "replay"])
            sub.add_argument("--provider", choices=choices, default="scripted")
        if name in {"submit", "resume"}:
            sub.add_argument("--allow-live", action="store_true")
            sub.add_argument("--model")
            sub.add_argument("--replay-file")
        if name in {"resume", "review", "approve", "report", "cancel", "activate-event", "advance-clock"}: sub.add_argument("--workflow", required=True)
        if name == "import-event": sub.add_argument("--event-file", required=True)
        if name == "advance-clock": sub.add_argument("--seconds", type=int, required=True)
        if name == "approve":
            sub.add_argument("--review-file", required=True)
            sub.add_argument("--approver", required=True)
        if name == "demo": sub.add_argument("--scenario", choices=sorted(p.name for p in (ROOT / "fixtures/dev").iterdir() if p.is_dir()), required=True)
    args = parser.parse_args(argv)
    try:
        selected_provider = getattr(args, "provider", "scripted")
        if args.command in {"submit", "resume"}:
            if args.provider == "responses":
                if args.replay_file:
                    raise ValueError("Responses cannot consume a replay fixture")
                from .responses import live_provider
                selected_provider = live_provider(args.model, args.allow_live)
            elif args.provider == "replay":
                if not args.replay_file or args.allow_live or args.model:
                    raise ValueError("replay requires only --replay-file, without live flags")
                from .replay import ReplayProvider
                selected_provider = ReplayProvider(args.replay_file)
            elif args.allow_live or args.model or args.replay_file:
                raise ValueError("provider options do not match the selected offline mode")
        if args.command == "demo": return demo(args.scenario, args.run_dir, args.provider)
        if args.command == "init": result = initialize(args.fixture, args.run_dir)
        elif args.command in {"submit", "resume"}:
            request = read_json(args.request if args.command == "submit" else Path(args.run_dir) / "request.json")
            if args.command == "resume":
                current = operator(args.run_dir, "report", workflow_id=args.workflow)
                if current["workflow_id"] != args.workflow: raise ValueError("workflow mismatch")
            result = act(args.run_dir, request, provider=selected_provider)
        elif args.command == "review":
            result, path = create_review(args.run_dir, args.workflow)
            result["review_file"] = str(path)
        elif args.command == "approve": result = approve_review(args.run_dir, args.workflow, args.review_file, args.approver)
        elif args.command == "cancel": result = operator(args.run_dir, "cancel", workflow_id=args.workflow)
        elif args.command == "activate-event": result = operator(args.run_dir, "activate_event", workflow_id=args.workflow)
        elif args.command == "import-event":
            from evaluation.scenarios import string_fields
            result = operator(args.run_dir, "import_event", **string_fields(read_json(args.event_file)))
        elif args.command == "advance-clock": result = operator(args.run_dir, "advance_clock", workflow_id=args.workflow, seconds=str(args.seconds))
        else: result = operator(args.run_dir, "report", workflow_id=args.workflow)
        print(json.dumps(result, indent=2))
        return 2 if args.command in {"submit", "resume"} and result["administrative_status"] != "COMPLETED" else 0
    except (ValueError, RuntimeError, AssertionError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
