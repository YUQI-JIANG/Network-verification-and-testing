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

## Prerequisites
Before running the framework, make sure the following tools are available:
- Python 3
- Batfish
- Docker (if Batfish is run through a Docker container)
- Standard Python libraries required by the scripts
- Access to a Moodle instance if you want to test the full Moodle-based workflow

## Recommended Environment
- A local machine with Python installed
- Docker running successfully
- Batfish service available before answer validation starts

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

### Part A — Generate routing questions

#### Step 1 — Go to the Automated question generation folder
Navigate to:
```bash
Latest Complete Script/Automated question generation/
```
This folder contains:

- moodle_xml_questions_generator.py
- Topology images used in the generated questions

#### Step 2 — Run the question generation script
Run:

```bash
python moodle_xml_questions_generator.py
```
This step generates quiz artifacts for Moodle import.

#### Step 3 — Check the generated outputs
You should find:
- routing_questions.xml
  
Moodle-compatible quiz file.
- routing_questions_meta.json

Metadata describing the generated routing questions.

#### Step 4 — Import the generated XML into Moodle
Use the generated routing_questions.xml file to import the quiz into Moodle.

At this point:
- students can view the generated routing questions
- the corresponding metadata file will later be used during answer validation

### Part B — Collect student answers
#### Step 5 — Export student responses from Moodle
After students complete the quiz, export the quiz responses from Moodle.

From your repository structure, the validation pipeline expects a JSON file such as:
```bash
Computer_Networking_Quiz_Responses.json
```
Place the exported response file in:
```bash
Latest Complete Script/Automated answer validation/
```
#### Step 6 — Make sure question metadata is available
The answer validation pipeline also needs the routing question metadata:
```bash
routing_questions_meta.json
```
Make sure the correct metadata file is available in:
```bash
Latest Complete Script/Automated answer validation/
```
This metadata should match the generated questions that students answered.

### Part C — Run automated answer validation
#### Step 7 — Go to the automated answer validation folder
Navigate to:
```bash
Latest Complete Script/Automated answer validation/
```
This folder contains:
- MAIN.py
- Batfish_automated_verification.py
- Computer_Networking_Quiz_Responses.json
- routing_questions_meta.json

#### Step 8 — Make sure Batfish is available
Before running the validation pipeline, make sure Batfish is ready.

If your setup uses Docker, start the Batfish-related container or service first.

#### Step 9 — Run the main grading pipeline
Run:
```bash
python MAIN.py
```
This is the main entry point for:

- parsing student answers
- constructing snapshots
- launching Batfish verification
- computing grading outputs
- exporting result files

## Output files produced during answer validation
After execution, inspect:
```bash
Output/Automated answer validation output/
```
### Main Outputs
- student_snapshots/

Contains per-student and per-question reconstructed snapshots.
- grading_results.csv
  
Summary grading file.
- moodle_import_total.csv
  
CSV prepared for Moodle-compatible grading import.

### Inside each per-question snapshot directory
For example:
```bash
student_snapshots/<student_identifier>/<question_id>/
```
You may find:
- configs/
  
Device configuration files generated for the snapshot.
- topology/
  
Topology description for the reconstructed scenario.
- grade.json
  
Structured grading result for that question.
- raw_output.txt
  
Raw verification output produced during analysis.

These files are useful for:
- debugging
- validation traceability
- explaining why a grade was assigned

## Core Verification Logic

The framework evaluates behavioral correctness, not textual similarity.

The main verified properties are:

Reachability: whether required destination prefixes are reachable from designated source nodes.

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

1. configs/ and topology/ define the Batfish snapshot.

2. raw_output.txt stores intermediate verification results.

3. grade.json stores structured grading results.
   
## Moodle Integration

This repository includes a proof-of-concept integration into a Moodle-based teaching workflow:

- Questions are exported as Moodle-compatible XML

- Student answers are processed automatically

- Final grades are exported as CSV for Moodle import

## Thesis Context

This repository accompanies a thesis on automated verification and evaluation of routing configurations.

The main contribution is a behavior-based grading methodology built around:

- Snapshot synthesis

- Batfish-based data-plane verification

- Scoped reachability and loop checks

- Deterministic mapping from verification outcomes to grading results

## Reproducibility

To support reproducibility, this repository provides:

- Implementation code

- Generated question artifacts

- Metadata

- Per-question snapshot artifacts

- Structured verification and grading outputs

## License

This project is released under the MIT License.

See the LICENSE file for details.
