# RL-CAPA Output Plots Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Align `runner.py run --algorithm rl-capa` outputs so one run emits both numeric results and plot artifacts for training and evaluation.

**Architecture:** Keep the current RL-CAPA training/evaluation entrypoints, but attach plotting at those boundaries. Training writes `training_summary.json` plus `training_curves.png`; evaluation writes `eval/summary.json` plus `tr_over_batches.png`, `cr_over_batches.png`, and `bpt_over_batches.png`; the root runner summary links both plot groups.

**Tech Stack:** Python, unittest, matplotlib, existing RL-CAPA trainer/evaluator, existing batch-report data model

---
