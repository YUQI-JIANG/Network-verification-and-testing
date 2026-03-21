# Automated Verification and Evaluation of Network Routing Configurations

This repository contains the implementation and selected artifacts for a thesis project on **automated verification and grading of routing configurations** using **Batfish-based data-plane analysis**.

Instead of comparing routing-table entries or configuration text directly, the framework evaluates the **forwarding behavior** induced by a student solution. Student routing answers are transformed into complete network snapshots, analyzed with **Batfish**, and mapped to deterministic grading outcomes based on **reachability** and **loop-safety** checks.

## Repository Structure

```text
Network-verification-and-testing
├── Latest Complete Script/
│   │
│   ├──── Automated answer validation/
│   │     ├── Batfish_automated_verification.py
│   │     ├── Computer_Networking_Quiz_Responses.json
│   │     ├── MAIN.py
│   │     └── routing_questions_meta.json
│   │
│   └── Automated question generation/
│       ├── Linear topology.png
│       ├── Routing in a loop topology.png
│       ├── Single server topology.png
│       └── moodle_xml_questions_generator.py
│
├── Output/
│   │
│   ├── Automated answer validation output/
│   │   ├── student_snapshots/User_Admin_user_at_example.com
│   │   │   ├── LINEAR_080/
│   │   │   │   ├──configs
│   │   │   │   │  ├──HA.cfg
│   │   │   │   │  ├──HB.cfg
│   │   │   │   │  ├──R1.cfg
│   │   │   │   │  └──R2.cfg
│   │   │   │   ├──topology
│   │   │   │   │  └──topology.json
│   │   │   │   ├──grade.json
│   │   │   │   └──raw_output.txt
│   │   │   ├── LOOP_042/
│   │   │   └── SINGLE_061/
│   │   │
│   │   ├── grading_results.csv
│   │   └── moodle_import_total.csv
│   │
│   └── Automated question generation output/
│       └── 20260214_153806
│           ├── routing_questions.xml
│           └── routing_questions_meta.json
│   
└── README.md
```

## Workflow Overview

The framework follows this end-to-end workflow:

1. Generate routing questions and metadata.

2. Export Moodle-compatible XML quiz files.

3. Collect student routing answers.

4. Parse answers and synthesize complete Batfish snapshots.

5. Run Batfish verification queries on the data plane.

6. Compute deterministic grading results.

7. Export structured outputs and CSV files for Moodle import.

## Step-by-Step Execution Guide

This section explains how to run the framework from start to finish.

### Step 1 — Prepare the input data
Before running the framework, prepare the following inputs:

- routing question definitions
- topology metadata
- target prefix sets
- student answer files

Make sure these files are placed in the expected input folders.

### Step 2 — Generate routing questions
Run the script responsible for question generation:

```bash

```
This step generates the routing questions and the corresponding metadata needed for later verification.






## Core Verification Logic

The framework evaluates behavioral correctness, not textual similarity.

The main verified properties are:

Reachability: whether required destination prefixes are reachable from designated source nodes;

Loop safety: whether forwarding loops affect the tested destination-prefix set.

Verification is intentionally scoped to the question-defined destination-prefix set, which makes the approach suitable for educational grading.

## Snapshot Artifacts

Each submission is materialized into per-question snapshot folders. A typical structure is:

```text
student_snapshots/
└── <student_identifier>/
    ├── SINGLE_<QID>/
    │   ├── configs/
    │   ├── topology/
    │   ├── grade.json
    │   └── raw_output.txt
    ├── LINEAR_<QID>/
    └── LOOP_<QID>/
```

These artifacts support traceability and reproducibility:

1. configs/ and topology/ define the Batfish snapshot;

2. raw_output.txt stores intermediate verification results;

3. grade.json stores structured grading results.

## Main Outputs

The repository includes example outputs such as:

1. routing_questions.xml – Moodle compatible question export

2. routing_questions_meta.json – structured topology and question metadata

3. grading_results.csv – grading results across question instances

4. moodle_import_total.csv – CSV export for Moodle grade import

5. grade.json – structured result for a single question instance

## Moodle Integration

This repository includes a proof-of-concept integration into a Moodle-based teaching workflow:

Questions are exported as Moodle-compatible XML;

Student answers are processed automatically;

Final grades are exported as CSV for Moodle import.

## Thesis Context

This repository accompanies a thesis on automated verification and evaluation of routing configurations.

The main contribution is a behavior-based grading methodology built around:

Snapshot synthesis;

Batfish-based data-plane verification;

Scoped reachability and loop checks;

Deterministic mapping from verification outcomes to grading results.

## Reproducibility

To support reproducibility, this repository provides:

Implementation code;

Generated question artifacts;

Metadata;

Per-question snapshot artifacts;

Structured verification and grading outputs.

## License

This project is released under the MIT License.

See the LICENSE file for details.
