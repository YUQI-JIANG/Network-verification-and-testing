""" 
Output Moodle XML (Essay Questions + Response Template)
Import Moodle: Question Bank → Import → Select "Moodle XML" 
"""

from __future__ import annotations
import base64
import ipaddress
import json
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from xml.sax.saxutils import escape

# Adjustable parameters
NUM_QUESTIONS = 100
ROWS_IN_TEMPLATE = 5 

OUTPUT_DIR = Path("Output")
OUTPUT_DIR.mkdir(exist_ok=True)

TOPO_IMAGES = [
    Path("Single server topology.png"),
    Path("topo_alt1.png"),
    Path("topo_alt2.png"),
]

PREFIX_POOL = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
]

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
XML_PATH  = OUTPUT_DIR / f"routing_quiz_{stamp}.xml"
META_PATH = OUTPUT_DIR / f"routing_questions_{stamp}.json"

# Utility functions
def pick_topology_image() -> str:
    for p in TOPO_IMAGES:
        if p.exists():
            img_b64 = base64.b64encode(p.read_bytes()).decode()
            return f"data:image/png;base64,{img_b64}"
    tiny_png = base64.b64encode(
        bytes.fromhex(
            "89504E470D0A1A0A0000000D4948445200000001000000010806000000"
            "1F15C4890000000A49444154789C6360000002000154A20F5B00000000"
            "49454E44AE426082"
        )
    ).decode()
    return f"data:image/png;base64,{tiny_png}"

def pick_two_lans(super_pool: ipaddress.IPv4Network) -> tuple[ipaddress.IPv4Network, ipaddress.IPv4Network]:
    prefix_len = random.choice([24, 25, 26])
    candidates = list(super_pool.subnets(new_prefix=prefix_len))
    net1, net2 = random.sample(candidates, 2)
    return net1, net2

def host_ips(net: ipaddress.IPv4Network) -> list[str]:
    """Return several readable host addresses (with subnet masks) within the network segment for use in h1/r1/r2/h2 assignment"""
    hosts = [str(ip) for ip in net.hosts()]
    choices = [hosts[1], hosts[5], hosts[10], hosts[-2]]
    random.shuffle(choices)
    return [f"{ip}/{net.prefixlen}" for ip in choices]

# New additions: Three tables (H1 / R / H2)
def build_device_table(caption: str, rows: int) -> str:
    """Generate a small table for each device, with columns: Network Prefix | Gateway | Interface"""
    head = (
        f'<h4 style="margin-top:18px">[{escape(caption)}] Routing Table</h4>'
        '<table border="1" cellpadding="6" cellspacing="0" '
        'style="border-collapse:collapse;text-align:center;min-width:680px;">'
        '<tr style="background:#f4f6f8;">'
        '<th style="width:60px;">Rule</th>'
        '<th style="width:260px;">Network Prefix</th>'
        '<th style="width:200px;">Gateway</th>'
        '<th style="width:160px;">Interface</th>'
        '</tr>'
    )
    body = []
    for i in range(1, rows + 1):
        body.append(f'<tr><td>{i}</td><td></td><td></td><td></td></tr>')
    tail = "</table>"
    return head + "".join(body) + tail

def build_three_tables_response(rows: int = ROWS_IN_TEMPLATE) -> str:
    """Combine the three tables H1, R, and H2 together and inject them into the editor as a response template"""
    return (
        build_device_table("H1", rows) +
        build_device_table("R",  rows) +
        build_device_table("H2", rows)
    )

def question_text_html(q: Dict[str, Any]) -> str:
    html = f"""
<p><b>ID:</b> {escape(q['qid'])}</p>
<p>Based on the topology below, calculate the <b>complete routing table</b> for <b>HA</b>, <b>R</b>, and <b>HB</b>.</p>
<p>Use the format: <b>Network Prefix | Gateway | Interface</b>.</p>
<p><img src="{q['data_uri']}" alt="topology" style="max-width:640px;border:1px solid #ccc;border-radius:6px"></p>

<h4>Subnets:</h4>
<ul>
  <li>neta : {escape(q['net1_cidr'])}</li>
  <li>netb : {escape(q['net2_cidr'])}</li>
</ul>

<h4>IP assignments:</h4>
<ul>
  <li>ha-eth0 : {escape(q['h1_ip'])}</li>
  <li>r-eth0  : {escape(q['r_eth0'])}</li>
  <li>r-eth1  : {escape(q['r_eth1'])}</li>
  <li>hb-eth0 : {escape(q['h2_ip'])}</li>
</ul>

<h4>Answer guidelines:</h4>
<ul>
  <li>Write <b>one route per row</b>, with no extra text. You can leave unused rows <b>blank</b>.</li>
  <li>Please fill <b>each device</b> in its own routing table: <b>[HA]</b>, <b>[R]</b>, <b>[HB]</b>.</li>
  <li>Use <b>0.0.0.0/0</b> for default network prefix.</li>
  <li>Use <b>*</b> for directly connected networks.</li>
  <li>Use <b>ethx</b> for interface.</li>
</ul>
""".strip()
    return html

def build_question_xml(q: Dict[str, Any], rows: int = ROWS_IN_TEMPLATE) -> str:
    """Assemble a single-question Moodle XML (Essay)
    - questiontext: The question stem (HTML)
    - responsetemplate: A pre-defined, editable table for the student's answer box"""
    name = escape(q["qid"])
    qtext = question_text_html(q)
    rtmpl = build_three_tables_response(rows)

    xml = f"""
  <question type="essay">
    <name><text>{name}</text></name>
    <questiontext format="html">
      <text><![CDATA[{qtext}]]></text>
    </questiontext>

    <responseformat>editor</responseformat>
    <responsefieldlines>16</responsefieldlines>
    <attachments>0</attachments>
    <graderinfo format="html"><text></text></graderinfo>

    <responsetemplate format="html">
      <text><![CDATA[{rtmpl}]]></text>
    </responsetemplate>
  </question>
""".rstrip()
    return xml

def build_quiz_xml(questions: List[Dict[str, Any]], rows: int = ROWS_IN_TEMPLATE) -> str:
    items = [build_question_xml(q, rows=rows) for q in questions]
    return '<?xml version="1.0" encoding="UTF-8"?>\n<quiz>\n' + "\n".join(items) + "\n</quiz>\n"

def make_question(qindex: int) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Generate data for one question (for XML and meta) according to original logic
    - Randomize two network segments (/24 ~ /26)
    - Select IPs (with masks) for h1, r_eth0, r_eth1, and h2
    - Inline topology diagram as data URI"""
    qid = f"Q{qindex:03}_{random.randint(1000,9999)}"
    super_pool = random.choice(PREFIX_POOL)
    net1, net2 = pick_two_lans(super_pool)

    # Select host IP (readable, with subnet mask)
    h1, r0, *_ = host_ips(net1)
    r1, h2, *_ = host_ips(net2)

    data_uri = pick_topology_image()

    # Field for XML rendering (name aligned with the title template)
    question_dict = {
        "qid": qid,
        "data_uri": data_uri,
        "net1_cidr": str(net1),
        "net2_cidr": str(net2),
        "h1_ip": h1,
        "r_eth0": r0,
        "r_eth1": r1,
        "h2_ip": h2,
    }

    # meta：The original structure is retained for grading purposes
    meta = {
        "qid": qid,
        "topology": "H1--net1--R--net2--H2",
        "nets": {"net1": str(net1), "net2": str(net2)},
        "ip_assignments": {
            "H1": {"eth0": h1, "net": "net1"},
            "R": {"eth0": r0, "eth1": r1},
            "H2": {"eth0": h2, "net": "net2"},
        },
        "difficulty": "basic-2lan-1router",
    }
    return question_dict, meta

# MAIN
def main():
    questions_for_xml: List[Dict[str, Any]] = []
    all_meta: List[Dict[str, Any]] = []

    for i in range(1, NUM_QUESTIONS + 1):
        q, meta = make_question(i)
        questions_for_xml.append(q)
        all_meta.append(meta)

    # Write XML
    xml_text = build_quiz_xml(questions_for_xml, rows=ROWS_IN_TEMPLATE)
    XML_PATH.write_text(xml_text, encoding="utf-8")

    # Write META JSON
    META_PATH.write_text(json.dumps(all_meta, indent=2), encoding="utf-8")

    print(f"[SUCCESS] Generated {NUM_QUESTIONS} questions! (Moodle XML)")
    print(f"     XML  : {XML_PATH}")
    print(f"     META : {META_PATH}")

if __name__ == "__main__":
    random.seed()
    main()