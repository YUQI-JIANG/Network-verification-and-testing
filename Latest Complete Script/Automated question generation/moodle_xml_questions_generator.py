#!/usr/bin/env python3
"""
Moodle XML + meta JSON generator for three routing-table question families:

1) single router:   HA -- R1 -- HB
2) linear topology: HA -- R1 -- R2 -- HB
3) loop topology:   HA -- R1 -- (R2,R3,R4 loop) -- HB

Design goals (aligned with your "Scheme A"):
- Each topology family has its own generator function (easy to extend later).
- One combined meta JSON for all questions (qid -> meta), so the verifier does one lookup.
- One combined Moodle XML that creates three Categories: /Routing/Single, /Routing/Linear, /Routing/Loop.
  Then Moodle can pick "1 random question from each category".

Notes:
- This script only *generates* questions/meta. The Batfish-based verifier consumes meta to build snapshots.
- Names used in meta are H1, H2, R, R1, R2, R3, R4, etc. Keep them consistent end-to-end.
"""

from __future__ import annotations

import base64
import json
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
import ipaddress

# =========================
# Adjustable parameters
# =========================

SEED = 20251218

NUM_SINGLE = 100
NUM_LINEAR = 100
NUM_LOOP   = 100

ts = datetime.now().strftime("%Y%m%d_%H%M%S")
OUT_DIR = Path("Output_v2") / ts
OUT_DIR.mkdir(parents=True)

OUT_XML  = OUT_DIR / "routing_questions.xml"
OUT_META = OUT_DIR / "routing_questions_meta.json"

# if you already have 3 diagram images, set them here.
IMG_SINGLE = Path("Single server topology.png") 
IMG_LINEAR = Path("Linear topology.png")  
IMG_LOOP   = Path("Routing in a loop topology.png")  

# Prefix length used for each link network
HOST_NET_PREFIX = 24   # HA-R1
P2P_LINK_PREFIX = 30   # R1-R2 

# =========================
# XML helpers (Moodle)
# =========================

def _xml_escape(s: str) -> str:
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;")
             .replace("'", "&apos;"))

def _cdata(s: str) -> str:
    # Moodle accepts CDATA; keep it simple
    return f"<![CDATA[{s}]]>"

def _category_question_xml(category_path: str) -> str:
    # category_path like "$course$/Routing/Single"
    return f"""  <question type="category">
    <category>
      <text>{_xml_escape(category_path)}</text>
    </category>
  </question>
"""

def _essay_question_xml(qname: str, qtext_html: str, response_template: str = "") -> str:
    # Minimal, Moodle-friendly "essay" question
    # You can extend grading options later; your verifier grades externally anyway.
    return f"""  <question type="essay">
    <name><text>{_xml_escape(qname)}</text></name>
    <questiontext format="html">
      <text>{_cdata(qtext_html)}</text>
    </questiontext>
    <generalfeedback format="html"><text>{_cdata("")}</text></generalfeedback>
    <defaultgrade>10.0000000</defaultgrade>
    <penalty>0.0000000</penalty>
    <hidden>0</hidden>
    <responseformat>editor</responseformat>
    <responserequired>1</responserequired>
    <responsefieldlines>15</responsefieldlines>
    <attachments>0</attachments>
    <attachmentsrequired>0</attachmentsrequired>
    <responsetemplate format="html">
      <text>{_cdata(response_template)}</text>
    </responsetemplate>
  </question>
"""

def build_quiz_xml(question_blocks: List[str]) -> str:
    return "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<quiz>\n" + "".join(question_blocks) + "</quiz>\n"


# =========================
# Network primitives
# =========================

def _rand_private_base() -> ipaddress.IPv4Network:
    """
    Pick a random /16 base inside RFC1918 (10/8, 172.16/12, 192.168/16).
    This gives enough room to carve multiple subnets of the target prefix (e.g., /24) without overlap.
    """
    choice = random.choice(["10", "172", "192"])
    if choice == "10":
        a = 10
        b = random.randint(0, 255)
        return ipaddress.ip_network(f"{a}.{b}.0.0/16", strict=False)
    elif choice == "172":
        a = 172
        b = random.randint(16, 31)
        return ipaddress.ip_network(f"{a}.{b}.0.0/16", strict=False)
    # 192.168
    else:
        return ipaddress.ip_network(f"192.168.{random.randint(0,255)}.0/16", strict=False)

def _pick_distinct_subnets_var(prefixlens: list[int]) -> list[ipaddress.IPv4Network]:
    """
    Produce len(prefixlens) distinct subnets with possibly different prefix lengths.
    All subnets are sampled from RFC1918 via a /16 base, and checked for overlap.
    """
    out: list[ipaddress.IPv4Network] = []
    attempts = 0

    while len(out) < len(prefixlens) and attempts < 5000:
        attempts += 1
        base = _rand_private_base()   # always /16

        target = prefixlens[len(out)]
        if not (16 <= target <= 30):
            raise ValueError("prefixlen must be in [16, 30] for this generator")

        # carve candidates of target prefix from base
        if base.prefixlen == target:
            cand = base
        elif base.prefixlen < target:
            cand = random.choice(list(base.subnets(new_prefix=target)))
        else:
            # base (/16) should never be longer than target, but keep safe
            continue

        if all(not cand.overlaps(x) for x in out):
            out.append(cand)

    if len(out) < len(prefixlens):
        raise RuntimeError("Failed to allocate non-overlapping subnets; adjust ranges/prefixlens.")

    return out

def _host_ip(net: ipaddress.IPv4Network, host_index: int) -> str:
    ip = net.network_address + host_index
    if ip not in net:
        raise ValueError(f"host_index {host_index} out of range for {net}")
    return str(ip)

def _cidr(ip: str, net: ipaddress.IPv4Network) -> str:
    return f"{ip}/{net.prefixlen}"

def _pick_index(net: ipaddress.IPv4Network, role: str) -> int:
    if net.prefixlen == 30:
        if role == "router_low":
            return 1
        elif role == "router_high":
            return 2
        else:  # host on /30 (rare, but keep safe)
            return 1
    # non-/30 (e.g., /24 host nets)
    if role == "router_low":
        return 2
    if role == "router_high":
        return 11
    return 6

def _iface(net: ipaddress.IPv4Network, role: str) -> str:
    return _cidr(_host_ip(net, _pick_index(net, role)), net)


# =========================
# Topology specs
# =========================

@dataclass(frozen=True)
class TopologyFamily:
    key: str                 # "single" | "linear" | "loop"
    category: str            # Moodle category suffix
    title: str               # Question statement title line
    image_path: Optional[Path]
    nets_order: List[str]    # display order for subnet table
    iface_order: List[str]   # display order for IP assignment table
    devices_for_tables: List[str]  # devices that must have routing tables in student answer


SINGLE = TopologyFamily(
    key="single",
    category="Single",
    title="Single router topology",
    image_path=IMG_SINGLE,
    nets_order=["neta", "netb"],
    iface_order=["ha", "hb", "r1a", "r1b"],
    devices_for_tables=["HA", "R1", "HB"],
)

LINEAR = TopologyFamily(
    key="linear",
    category="Linear",
    title="Linear topology",
    image_path=IMG_LINEAR,
    nets_order=["neta1", "net12", "net2b"],
    iface_order=["ha", "hb", "r1a", "r12", "r21", "r2b"],
    devices_for_tables=["HA", "R1", "R2", "HB"],
)

LOOP = TopologyFamily(
    key="loop",
    category="Loop",
    title="Routing in a loop topology",
    image_path=IMG_LOOP,
    nets_order=["neta1", "net12", "net24", "net13", "net34", "net4b"],
    iface_order=["ha", "hb", "r1a", "r12", "r13", "r21", "r24", "r31", "r34", "r42", "r43", "r4b"],
    devices_for_tables=["HA", "R1", "R2", "R3", "R4", "HB"],
)


# =========================
# Meta + HTML builders
# =========================

def _img_html(p: Optional[Path]) -> str:
    if not p:
        return ""
    data = p.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    # Assume PNG/JPG by file suffix; default to png
    mime = "image/png"
    if p.suffix.lower() in [".jpg", ".jpeg"]:
        mime = "image/jpeg"
    return f'<div style="margin:10px 0;"><img style="max-width:100%;height:auto" src="data:{mime};base64,{b64}"/></div>'

def _subnets_ul(nets: Dict[str, str], order: List[str]) -> str:
    lis = []
    for k in order:
        lis.append(f"<li><b>{_xml_escape(k)}</b>: {_xml_escape(nets[k])}</li>")
    return "<ul>" + "".join(lis) + "</ul>"

def _ip_assign_ul(assign_flat: Dict[str, str], order: List[str]) -> str:
    lis = []
    for k in order:
        lis.append(f"<li><b>{_xml_escape(k)}</b>: {_xml_escape(assign_flat[k])}</li>")
    return "<ul>" + "".join(lis) + "</ul>"

def _answer_guidelines_html() -> str:
    return """
<ul>
  <li>Write <b>one route per row</b>, with no extra text. You can leave unused rows blank.</li>
  <li>Please fill each device in its own routing table: <b>[HA], [R1], [HB]</b> (or more, depending on topology).</li>
  <li>Use <b>0.0.0.0/0</b> for the default network prefix.</li>
  <li>Use <b>*</b> for directly connected networks.</li>
  <li>Use <b>ethX</b> for the interface name.</li>
</ul>
"""

def build_question_html(qid: str, family: TopologyFamily, nets: Dict[str, str], assign_flat: Dict[str, str]) -> str:
    return f"""
<div>
  <p><b>ID:</b> {qid}</p>
  <p>Based on the topology below, calculate the <b>complete routing table</b> for {", ".join(family.devices_for_tables)}.</p>
  <p>Use the format: <b>Network Prefix | Gateway | Interface</b>.</p>
  {_img_html(family.image_path)}
  <h3>Subnets</h3>
  {_subnets_ul(nets, family.nets_order)}
  <h3>IP assignments</h3>
  {_ip_assign_ul(assign_flat, family.iface_order)}
  <h3>Answer guidelines</h3>
  {_answer_guidelines_html()}
</div>
"""

def _build_device_table_html(device: str, rows: int = 5) -> str:
    """
    Build a formatted HTML routing table for one device.
    """

    return f"""
    <div style="margin-top:18px;">
      <h4 style="margin-bottom:6px;">[{_xml_escape(device)}] Routing Table</h4>
      <table border="1" cellpadding="6" cellspacing="0"
             style="border-collapse:collapse;
                    text-align:center;
                    min-width:700px;
                    font-size:14px;">
        <tr style="background-color:#f2f4f7;">
          <th style="width:60px;">Rule</th>
          <th style="width:260px;">Network Prefix</th>
          <th style="width:200px;">Gateway</th>
          <th style="width:160px;">Interface</th>
        </tr>
        {''.join(
            f'<tr><td>{i}</td><td></td><td></td><td></td></tr>'
            for i in range(1, rows + 1)
        )}
      </table>
    </div>
    """

def build_response_template(family: TopologyFamily, rows: int = 5) -> str:
    """
    Build routing table templates for all required devices
    in the given topology family.
    """

    return "".join(
        _build_device_table_html(dev, rows=rows)
        for dev in family.devices_for_tables
    )

# =========================
# Family generators
# =========================

def gen_single(qid: str) -> Dict[str, Any]:
    # Two LANs: neta, netb
    neta, netb = _pick_distinct_subnets_var([HOST_NET_PREFIX, HOST_NET_PREFIX])
    nets = {"neta": str(neta), "netb": str(netb)}

    ip_assignments = {
        "HA": {"eth0": _iface(neta, "host"), "net": "neta"},
        "R1": {
            "eth0": _iface(neta, "router_low"),
            "eth1": _iface(netb, "router_low")
        },
        "HB": {"eth0": _iface(netb, "host"), "net": "netb"}
    }

    # Flattened for question statement (same as your screenshot style)
    assign_flat = {
        "ha": f"{ip_assignments['HA']['eth0']}",
        "hb": f"{ip_assignments['HB']['eth0']}",
        "r1a": f"{ip_assignments['R1']['eth0']}",
        "r1b": f"{ip_assignments['R1']['eth1']}",
    }

    meta = {
        "qid": qid,
        "type": "single",
        "topology": "HA--neta--R1--netb--HB",
        "nets": nets,
        "ip_assignments": ip_assignments,
    }
    return {"meta": meta, "nets": nets, "assign_flat": assign_flat}

def gen_linear(qid: str) -> Dict[str, Any]:
    # Three networks: neta1 (ha-r1), net12 (r1-r2), net2b (r2-hb)
    neta1, net12, net2b = _pick_distinct_subnets_var(
        [HOST_NET_PREFIX, P2P_LINK_PREFIX, HOST_NET_PREFIX]
    )
    nets = {"neta1": str(neta1), "net12": str(net12), "net2b": str(net2b)}

    ip_assignments = {
        "HA": {"eth0": _iface(neta1, "host"), "net": "neta1"},
        "R1": {
            "eth0": _iface(neta1, "router_low"),
            "eth1": _iface(net12, "router_low"),
        },
        "R2": {
            "eth0": _iface(net12, "router_high"),
            "eth1": _iface(net2b, "router_low"),
        },
        "HB": {"eth0": _iface(net2b, "host"), "net": "net2b"},
    }

    assign_flat = {
        "ha":  ip_assignments["HA"]["eth0"],
        "hb":  ip_assignments["HB"]["eth0"],
        "r1a": ip_assignments["R1"]["eth0"],
        "r12": ip_assignments["R1"]["eth1"],
        "r21": ip_assignments["R2"]["eth0"],
        "r2b": ip_assignments["R2"]["eth1"],
    }

    meta = {
        "qid": qid,
        "type": "linear",
        "topology": "HA--neta1--R1--net12--R2--net2b--HB",
        "nets": nets,
        "ip_assignments": ip_assignments,
    }
    return {"meta": meta, "nets": nets, "assign_flat": assign_flat}

def gen_loop(qid: str) -> Dict[str, Any]:
    # 6 link networks:
    # neta1: ha-r1   (host segment)
    # net12: r1-r2   (p2p)
    # net13: r1-r3   (p2p)
    # net24: r2-r4   (p2p)
    # net34: r3-r4   (p2p)
    # net4b: r4-hb   (host segment)
    neta1, net12, net13, net24, net34, net4b = _pick_distinct_subnets_var(
        [HOST_NET_PREFIX, P2P_LINK_PREFIX, P2P_LINK_PREFIX, P2P_LINK_PREFIX, P2P_LINK_PREFIX, HOST_NET_PREFIX]
    )

    nets = {
        "neta1": str(neta1),
        "net12": str(net12),
        "net13": str(net13),
        "net24": str(net24),
        "net34": str(net34),
        "net4b": str(net4b),
    }

    ip_assignments = {
        "HA": {"eth0": _iface(neta1, "host"), "net": "neta1"},

        "R1": {
            "eth0": _iface(neta1, "router_low"),
            "eth1": _iface(net12, "router_low"),
            "eth2": _iface(net13, "router_low"),
        },

        "R2": {
            "eth0": _iface(net12, "router_high"),
            "eth1": _iface(net24, "router_low"),
        },

        "R3": {
            "eth0": _iface(net13, "router_high"),
            "eth1": _iface(net34, "router_low"),
        },

        "R4": {
            "eth0": _iface(net24, "router_high"),
            "eth1": _iface(net34, "router_high"),
            "eth2": _iface(net4b, "router_low"),
        },

        "HB": {"eth0": _iface(net4b, "host"), "net": "net4b"},
    }

    assign_flat = {
        "ha":  ip_assignments["HA"]["eth0"],
        "hb":  ip_assignments["HB"]["eth0"],
        "r1a": ip_assignments["R1"]["eth0"],
        "r12": ip_assignments["R1"]["eth1"],
        "r13": ip_assignments["R1"]["eth2"],
        "r21": ip_assignments["R2"]["eth0"],
        "r24": ip_assignments["R2"]["eth1"],
        "r31": ip_assignments["R3"]["eth0"],
        "r34": ip_assignments["R3"]["eth1"],
        "r42": ip_assignments["R4"]["eth0"],
        "r43": ip_assignments["R4"]["eth1"],
        "r4b": ip_assignments["R4"]["eth2"],
    }

    meta = {
        "qid": qid,
        "type": "loop",
        "topology": "HA--neta1--R1--net12--R2--net24--R4--net4b--HB;R1--net13--R3--net34--R4",
        "nets": nets,
        "ip_assignments": ip_assignments,
    }
    return {"meta": meta, "nets": nets, "assign_flat": assign_flat}


# =========================
# Main
# =========================

def main() -> None:
    random.seed(SEED)

    # Build one XML with categories, and one combined meta json
    blocks: List[str] = []
    meta_all: Dict[str, Any] = {}

    # Category: Single
    blocks.append(_category_question_xml("$course$/Routing/Single"))
    for i in range(1, NUM_SINGLE + 1):
        qid = f"SINGLE_{i:03d}"
        g = gen_single(qid)
        qhtml = build_question_html(qid, SINGLE, g["nets"], g["assign_flat"])
        qname = qid
        blocks.append(_essay_question_xml(qname, qhtml, build_response_template(SINGLE, rows=2)))
        meta_all[qid] = g["meta"]

    # Category: Linear
    blocks.append(_category_question_xml("$course$/Routing/Linear"))
    for i in range(1, NUM_LINEAR + 1):
        qid = f"LINEAR_{i:03d}"
        g = gen_linear(qid)
        qhtml = build_question_html(qid, LINEAR, g["nets"], g["assign_flat"])
        blocks.append(_essay_question_xml(qid, qhtml, build_response_template(LINEAR, rows=3)))
        meta_all[qid] = g["meta"]

    # Category: Loop
    blocks.append(_category_question_xml("$course$/Routing/Loop"))
    for i in range(1, NUM_LOOP + 1):
        qid = f"LOOP_{i:03d}"
        g = gen_loop(qid)
        qhtml = build_question_html(qid, LOOP, g["nets"], g["assign_flat"])
        blocks.append(_essay_question_xml(qid, qhtml, build_response_template(LOOP, rows=4)))
        meta_all[qid] = g["meta"]

    OUT_XML.write_text(build_quiz_xml(blocks), encoding="utf-8")
    OUT_META.write_text(json.dumps(meta_all, indent=2), encoding="utf-8")

    print(f"XML: {OUT_XML} ({len(meta_all)} questions)")
    print(f"META: {OUT_META}")

if __name__ == "__main__":
    main()