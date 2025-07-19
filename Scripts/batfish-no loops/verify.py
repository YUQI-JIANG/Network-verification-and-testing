from pybatfish.client.commands import bf_session 
from pybatfish.question import load_questions, bfq 
from pathlib import Path

# global constants
SNAPSHOT_PATH = "D:/batfish-demo2"    

# connecting to Batfish and load the snapshot
bf_session.host = "localhost"
bf_session.init_snapshot(SNAPSHOT_PATH, name="demo-snap", overwrite=True)

# register all built-in Batfish questions
load_questions()

# helper: discover node names from *.cfg filenames
def cfg_files_nodes(dir_path: str) -> list[str]:
    cfg_paths = Path(dir_path).glob("*.cfg") 
    return sorted(p.stem for p in cfg_paths)

# helper: discover all directly‑connected prefixes of a node
def connected_prefixes(node: str) -> set[str]:
    routes = bfq.routes(nodes=node).answer().frame()
    mask   = routes["Protocol"].isin({"connected"}) 
    return set(routes[mask]["Network"])

# helper: reachability test (True → TraceCount ≥1)
def reachable(src: str, dst_prefix: str) -> bool:
    reach_df = bfq.reachability(
            pathConstraints={"startLocation": src}, # source node
            headers={"dstIps": dst_prefix} # destination prefix
         ).answer().frame() # return dataframe
    return not reach_df.empty 

# obtain the nodes list
SRC_NODES = cfg_files_nodes(SNAPSHOT_PATH + "/configs")
print("\nNodes to be graded:", SRC_NODES)

# obtain the global bag_net
bag_net: set[str] = set()
for n in SRC_NODES:
    bag_net.update(connected_prefixes(n))

bag_net = sorted(bag_net)
print("\nBAG_NET (all directly‑connected prefixes):")
for p in bag_net:
    print(" •", p)

# reachability check
print("\n========== Reachability Check (reachability) ==========")
total_tests   = len(SRC_NODES) * len(bag_net)
passed_tests  = 0
for node in SRC_NODES:
    for net in bag_net:
        ok = reachable(node, net)
        passed_tests += ok
        print(f"{node:>8s} ➜ {net:<18s} {'Reachable' if ok else 'Unreachable'}")

reach_index = passed_tests / total_tests if total_tests else 0
print(f"\nReachability index  = {passed_tests}/{total_tests} = {reach_index:.2f}")

# loop check
print("\n========== Loop Check (detectLoops) ==========")
loop_df = bfq.detectLoops().answer().frame()
loop_idx = 1 if loop_df.empty else 0 
if loop_idx:
    print("No loops found.")
else:
    print(loop_df)    

print(f"\nLoop index = {loop_idx:.2f}")

# printing results
print("\n========== Grading Result ==========")
print(f"• Reachability index : {reach_index:.2f}")
print(f"• Loop index         : {loop_idx:.2f}")