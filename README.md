# Automated Verification and Evaluation of Routing Configurations

This repository contains the implementation and selected artifacts for a thesis project on **automated verification and grading of routing configurations** using **Batfish-based data-plane analysis**.

The project targets educational routing exercises. Instead of comparing routing-table entries or configuration text directly, it evaluates the **forwarding behavior** induced by a student solution. Student routing answers are transformed into complete network snapshots, analyzed with **Batfish**, and mapped to deterministic grading outcomes based on **reachability** and **loop-safety** checks.

---

## Repository Overview

The repository is organized into three main parts:

- **Automated question generation**  
  Generates Moodle-compatible XML quiz questions and metadata for predefined routing topology families.

- **Automated answer validation**  
  Parses student routing answers, synthesizes per-question Batfish snapshots, runs verification queries, and computes grades.

- **Output artifacts**  
  Stores generated questions, per-student per-question snapshots, verification outputs, and CSV exports for Moodle import.

---

## Project Motivation

Routing exercises are a core component of computer networking education, but grading them manually is slow and difficult to scale. Direct comparison of routing-table entries is also unreliable:

- different routing tables may still induce the same forwarding behavior;
- small-looking differences may cause unreachable prefixes or forwarding loops;
- educational grading should focus on whether the solution satisfies the **required network behavior**.

This project addresses the problem by formulating grading as **verification of scoped data-plane properties**.

---

## Main Idea

The framework follows three main steps:

1. **Snapshot synthesis**  
   Student routing answers are combined with topology and IP-address metadata to reconstruct a complete network snapshot.

2. **Behavior-based verification**  
   Batfish computes the resulting data plane and answers verification queries, mainly:
   - reachability;
   - loop-safety.

3. **Deterministic result mapping**  
   Verification outcomes are converted into a final score through a simple decision rule.

The focus of grading is **behavioral correctness**, not textual similarity.

---

## Verified Properties

### Reachability
The framework checks whether required destination prefixes are reachable from designated source nodes.

### Loop Safety
The framework checks whether forwarding loops affect the flows relevant to the question.

### Verification Scope
Verification is intentionally **scoped to the question-defined destination-prefix set**.  
This is suitable for educational grading, where the goal is to assess whether a student solution satisfies the stated requirements of the exercise, rather than to certify full-network correctness under all possible flows.

---

## Scoring Logic

The grading logic is intentionally simple and deterministic:

- if required reachability is incomplete, the score is **0**;
- if reachability is complete but a relevant loop exists, the score is **partial**;
- if reachability is complete and no relevant loop is found, the score is **full**.

This makes grading:

- repeatable,
- interpretable,
- and suitable for large classes.

---

## Repository Structure

```text
Latest Complete Script/
├── Automated answer validation/
│   ├── Batfish_automated_verification_...
│   ├── Computer_Networking_Quiz_R...
│   ├── MAIN.py
│   └── routing_questions_meta.json
│
├── Automated question generation/
│   ├── Linear topology.png
│   ├── Routing in a loop topology.png
│   ├── Single server topology.png
│   └── moodle_xml_questions_gener...
│
├── Output/
│
├── Automated answer validation output/
│   ├── student_snapshots/User_Admin...
│   │   ├── LINEAR_080/
│   │   ├── LOOP_042/
│   │   └── SINGLE_061/
│   ├── grading_results.csv
│   └── moodle_import_total.csv
│
├── Automated question generation output/
│   ├── routing_questions.xml
│   └── routing_questions_meta.json
│
└── README.md
