"""
Multi-student Multi-question Grading Pipeline
- Generates per-question snapshots
- Calls verify.py with ABSOLUTE PATH
- Writes all snapshots to: student_snapshots/<student>/<qid>/
"""

import json
import re
import subprocess
import shutil
import csv
from pathlib import Path
from typing import Dict, Any, List, Tuple
import time

BASE = Path(__file__).resolve().parent

STU_JSON = BASE / "Computer_Networking_Quiz_Responses.json"
META_JSON = BASE / "routing_questions_meta.json"
VERIFY = BASE / "Batfish_automated_verification.py"
SNAP_ROOT = BASE / "student_snapshots"
CSV_OUT = BASE / "grading_results.csv"
CSV_OUT_TOTAL = BASE / "moodle_import_total.csv"

# Basic utility functions
def split_ip_mask(cidr: str):
    """Convert 10.1.1.2/24 → (10.1.1.2, 255.255.255.0)"""
    if "/" not in cidr:
        raise ValueError(f"Invalid CIDR (missing '/'): {cidr}")
    ip, plen = cidr.split("/")
    plen = int(plen)
    mask = (0xFFFFFFFF << (32 - plen)) & 0xFFFFFFFF
    mask_str = ".".join(str((mask >> (8*i)) & 0xFF) for i in reversed(range(4)))
    return ip, mask_str

def find_question_response_pairs(attempt: Dict[str, Any]):
    """Find (questionN, responseN) pairs"""
    q_re = re.compile(r"^question(\d+)$")
    r_re = re.compile(r"^response(\d+)$")
    pairs = {}
    
    for key, value in attempt.items():
        m = q_re.match(key)
        if m:
            pairs.setdefault(int(m.group(1)), {})["q"] = value
        m = r_re.match(key)
        if m:
            pairs.setdefault(int(m.group(1)), {})["r"] = value

    out = []
    for idx in sorted(pairs.keys()):
        q = pairs[idx].get("q", "")
        r = pairs[idx].get("r", "")
        out.append((idx, q, r))
    return out

def extract_qid(text: str) -> str:
    """Extract QID from question text."""
    m = re.search(r"\bID:\s*([A-Za-z]+_\d+)\b", text)
    if not m:
        raise ValueError("Missing or invalid ID")
    return m.group(1)

def parse_rtable(raw: str) -> Dict[str, List[Dict[str, str]]]:
    """Parse student's routing table into route dict"""
    raw = raw.replace("\xa0", " ")
    raw = re.sub(r"[\u2000-\u200B\u202F\u205F]", " ", raw)
    raw = re.sub(r"\s+(\[[A-Za-z0-9_]+\]\s*ROUTING TABLE)", r"\t\t\1", raw)
    
    fields = [f.strip() for f in raw.split("\t\t") if f.strip()]
    routes = {}
    dev = None
    buf = []

    for f in fields:
        m = re.match(r"^\[([A-Za-z0-9_]+)\]", f)
        if m:
            dev = m.group(1)
            routes[dev] = []
            buf = []
            continue

        buf.append(f)
        if len(buf) == 4:
            _, prefix, gw, iface = buf
            if dev is not None and prefix and "/" in prefix:
                routes[dev].append({"prefix": prefix, "gw": gw, "iface": iface})
            buf = []
    return routes

# Automatic snapshot generator
def generate_snapshot(meta: Dict[str, Any],
                      routes: Dict[str, List[Dict[str, str]]],
                      snap_dir: Path):
    
    """Generate configs/ and topology/ into snapshot dir"""
    if snap_dir.exists():
        shutil.rmtree(snap_dir)
    snap_dir.mkdir(parents=True)

    cfg = snap_dir / "configs"
    topo = snap_dir / "topology"
    cfg.mkdir()
    topo.mkdir()

    assign = meta["ip_assignments"]

    def gen_interfaces(dev):
        """Automatic interface generation"""
        out = []
        if dev not in assign:
            return out

        for iface, cidr in assign[dev].items():
            if "/" not in cidr:
                continue
            ip, mask = split_ip_mask(cidr)
            out.append(f"interface {iface}")
            out.append(f" ip address {ip} {mask}")
            out.append("!")
        return out
    
    def gen_routes(dev):
        """Static routes from student routing table"""
        out = []
        for r in routes.get(dev, []):
            if r["gw"] == "*":
                continue
            if "/" not in r["prefix"]:
                continue
            net, m = split_ip_mask(r["prefix"])
            out.append(f"ip route {net} {m} {r['gw']}")
        return out

    for dev in assign.keys(): 
        """Generate all device configs""" 
        cfg_lines = [
            f"hostname {dev}",
            *gen_interfaces(dev),
            *gen_routes(dev),
            ""
        ]
        (cfg / f"{dev}.cfg").write_text("\n".join(cfg_lines), encoding="utf-8")

    # TOPOLOGY (from meta["topology"])
    topo_str = meta.get("topology", "")
    parts = [p.strip() for p in topo_str.split("--") if p.strip()]
    devices = [p for p in parts if p[0].isalpha() and p[0].isupper()]

    links = []
    for i in range(len(devices) - 1):
        links.append([devices[i], devices[i + 1]])

    (topo / "topology.json").write_text(json.dumps({"links": links}, indent=2), encoding="utf-8")

# Run Batfish-Verify.py
def run_verify(snapshot_dir: Path, qid: str, lastname: str, firstname: str, email: str) -> float:
    """Run Batfish verification script and return elapsed time in seconds."""
    t0 = time.perf_counter()

    result = subprocess.run(
        ["python", str(VERIFY), str(snapshot_dir), qid, lastname, firstname, email],
        cwd=str(BASE),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace"
    )

    t1 = time.perf_counter()

    # keep your existing behavior
    print(result.stdout)
    if result.returncode != 0:
        print("VERIFY STDERR:", result.stderr)

    return t1 - t0

# MAIN
def main():
    # Reset CSV
    if CSV_OUT.exists():
        CSV_OUT.unlink()

    SNAP_ROOT.mkdir(exist_ok=True)

    all_data = json.loads(STU_JSON.read_text(encoding="utf-8"))
    meta_raw = json.loads(META_JSON.read_text(encoding="utf-8"))

    if isinstance(meta_raw, dict):
        meta_dict = meta_raw
    else:
        meta_dict = {q["qid"]: q for q in meta_raw}

    header = ["email", "lastname", "firstname", "qid", "grade",
              "reachability index", "loop index",
              "snapshot_time_s", "batfish_time_s", "total_time_s"]
    
    total_by_email = {}

    with CSV_OUT.open("w", newline="", encoding="utf-8") as fcsv:
        w = csv.writer(fcsv)
        w.writerow(header)
    
        for stu_block in all_data:
            if isinstance(stu_block, list):
                attempt = stu_block[0]
            else:
                attempt = stu_block

            lastname = attempt.get("lastname", "NA")
            firstname = attempt.get("firstname", "NA")
            email_raw = attempt.get("emailaddress", "NA").strip()
            email_safe = email_raw.replace(" ", "_").replace("@", "_at_")

            stu_dir = SNAP_ROOT / f"{lastname}_{firstname}_{email_safe}"
            stu_dir.mkdir(exist_ok=True)

            pairs = find_question_response_pairs(attempt)

            for _, qtext, rtext in pairs:
                qid = extract_qid(qtext)
                meta = meta_dict[qid]
                routes = parse_rtable(rtext)

                qdir = stu_dir / qid
                
                t_total0 = time.perf_counter()
                t_snap0 = time.perf_counter()
                generate_snapshot(meta, routes, qdir)
                snapshot_time = time.perf_counter() - t_snap0

                verify_time = run_verify(qdir, qid, lastname, firstname, email_raw)
                batfish_time = verify_time

                total_time = time.perf_counter() - t_total0
                # read grade.json
                grade_path = qdir / "grade.json"
                grade_obj = json.loads((qdir / "grade.json").read_text("utf-8"))
                grade_obj["Snapshot generation time (s)"] = snapshot_time
                grade_obj["Batfish verification time (s)"] = batfish_time
                grade_obj["Total grading time (s)"] = total_time
                grade_path.write_text(json.dumps(grade_obj, indent=2), encoding="utf-8")
                w.writerow([
                    grade_obj["email"],
                    grade_obj["lastname"],
                    grade_obj["firstname"],
                    grade_obj["qid"],
                    grade_obj["Grade"],
                    grade_obj["Reachability index"],
                    grade_obj["Loop index"],
                    f"{snapshot_time:.6f}",
                    f"{batfish_time:.6f}",
                    f"{total_time:.6f}",
                ])
                g = float(grade_obj["Grade"])
                total_by_email[email_raw] = total_by_email.get(email_raw, 0.0) + g
    
    CSV_OUT_TOTAL = BASE / "moodle_import_total.csv"

    with CSV_OUT_TOTAL.open("w", newline="", encoding="utf-8") as f2:
        w2 = csv.writer(f2)
        w2.writerow(["email", "grade"])
        for email_raw, total in sorted(total_by_email.items()):
            w2.writerow([email_raw, total])

    print("==== Automated Grading Complete! ====")
    print(f"All Students' Results Saved → {CSV_OUT}")
    print(f"Moodle Import CSV Saved → {CSV_OUT_TOTAL}")

if __name__ == "__main__":
    main()