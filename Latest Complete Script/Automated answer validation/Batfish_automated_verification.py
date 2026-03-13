"""
Generates:
    • grade.json
    • raw_output.txt

Usage:
    python verify.py "<abs_snapshot_dir>" "<qid>" "<lastname>" "<firstname>" "<email>"
"""

import sys
import json
from pathlib import Path
from pybatfish.client.commands import bf_session
from pybatfish.question import load_questions, bfq

# Helpers for writing results
def write_outputs(snapshot_dir: Path, raw: str, grade_obj: dict):
    """Write raw_output.txt + grade.json inside snapshot_dir."""
    (snapshot_dir / "raw_output.txt").write_text(raw, encoding="utf-8")
    (snapshot_dir / "grade.json").write_text(json.dumps(grade_obj, indent=2),
                                             encoding="utf-8")

def cfg_files_nodes(dir_path: str) -> list[str]:
    cfg_paths = Path(dir_path).glob("*.cfg")
    return sorted(p.stem for p in cfg_paths)

def connected_prefixes(node: str) -> set[str]:
    routes = bfq.routes(nodes=node).answer().frame()
    mask = routes["Protocol"].isin({"connected"})
    return set(routes[mask]["Network"])

def reachable(src: str, dst_prefix: str) -> bool:
    reach_df = bfq.reachability(
        pathConstraints={"startLocation": src},
        headers={"dstIps": dst_prefix}
    ).answer().frame()
    return not reach_df.empty

# Main verify logic
def main():
    # Parse CLI arguments
    if len(sys.argv) != 6:
        print("Usage: python verify.py <snapshot_dir> <qid> <lastname> <firstname> <email>")
        sys.exit(1)

    snapshot_dir = Path(sys.argv[1]).resolve()
    qid = sys.argv[2]
    lastname = sys.argv[3]
    firstname = sys.argv[4]
    email = sys.argv[5]

    configs_path = snapshot_dir / "configs"

    if not configs_path.exists():
        print(f"ERROR: configs/ not found in snapshot_dir: {snapshot_dir}")
        sys.exit(2)

    # Start capturing raw output
    raw_log = []
    def log(x): raw_log.append(str(x))

    # Connect to Batfish
    bf_session.host = "localhost"
    bf_session.init_snapshot(str(snapshot_dir), name=qid, overwrite=True)
    load_questions()

    # Step 1: List nodes
    SRC_NODES = cfg_files_nodes(str(configs_path))
    log("\nEvaluation Nodes:")
    for n in SRC_NODES:
        log(f" • {n}")

    # Step 2: Obtain all directly-connected prefixes
    bag_net = set()
    for n in SRC_NODES:
        bag_net.update(connected_prefixes(n))
    bag_net = sorted(bag_net)

    log("\nDestination Prefix Set (BAG-NET):")
    for p in bag_net:
        log(f" • {p}")

    # Step 3: Reachability check
    log("\n========= Reachability Check ==========")

    total_tests = len(SRC_NODES) * len(bag_net)
    passed_tests = 0
    failed = []

    for node in SRC_NODES:
        for net in bag_net:
            ok = reachable(node, net)
            passed_tests += ok
            line = f"{node:>8s} ➜ {net:<18s} {'Reachable' if ok else 'Unreachable'}"
            log(line)
            if not ok:
                failed.append((node, net))

    reach_index = passed_tests / total_tests if total_tests else 0.0
    log(f"\nReachability index = {passed_tests}/{total_tests} = {reach_index:.2f}")

    # Step 4: Loop check
    log("\n=========== Loop Check ============")
    loop_df = bfq.detectLoops().answer().frame()

    loop_found = False

    if loop_df.empty:
        log("No loops found (global):")
    else:  
        for _, row in loop_df.iterrows():
            flow_str = str(row["Flow"])

            for prefix in bag_net:
                if prefix.split("/")[0] in flow_str:
                    log(f"Loop related to test prefix {prefix}")
                    log(row)
                    loop_found = True
                    break

            if loop_found:
                break
        
        if not loop_df.empty and not loop_found:
            log("Global loops detected, but none is relevant to the destination prefix set (BAG-NET).")

    loop_index = 0 if loop_found else 1
    log(f"\nLoop index = {loop_index}")

    # Step 5: Grade
    if reach_index < 1.0:
        grade = 0
    else:
        grade = 10 if loop_index == 1 else 5

    log("\n=========== Final Grade ============")
    log(f"Grade = {grade}")

    # Write outputs
    grade_obj = {
        "qid": qid,
        "lastname": lastname,
        "firstname": firstname,
        "email": email,
        "Reachability index": reach_index,
        "Loop index": loop_index,
        "Grade": grade
    }

    write_outputs(snapshot_dir, "\n".join(raw_log), grade_obj)

    # Print summary to console
    print(f"qid={qid}, Grade={grade}, Reachability index={reach_index:.2f}, Loop index={loop_index}")

if __name__ == "__main__":
    main()