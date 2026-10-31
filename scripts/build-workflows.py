#!/usr/bin/env python3
"""
Writes the bulk RNA-seq workflow definitions (workflow/*.json, the body of
POST /compute/workflows/definitions). Add "organizationId": "N:organization:..." to the body when
posting: without it the workflow belongs to no workspace and the Workflow Library doesn't list it.
Each step's cpu/memory comes from its app's app.yml runtime (the sibling repo ../<app>), rounded up to
a size Fargate offers, and each step pins the newest release tag at or before the checked-out commit.
The helpers are the spatial suite's (../workflow-spatial-transcriptomics/scripts/build-workflows.py).

Usage: scripts/build-workflows.py
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "spatial_builder", ROOT.parent / "workflow-spatial-transcriptomics" / "scripts" / "build-workflows.py")
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)
step, output, ROW = B.step, B.output, B.ROW


def interface(id_, name, description, row):
    return {"id": id_, "name": name, "description": description, "position": {"x": 40, "y": 40 + ROW * row}}


DE = lambda col, row, links, depends: step("de", "bulk-de", col, row, depends, links,
                                            {"DESIGN": "~ condition"})


def from_fastq():
    steps = [
        # No genome input, so no decoys: the transcripts-only build peaked at 3.9 GB (rnaseq-index README),
        # far below the app's default, which is sized for a genome-decoy build.
        {**step("index", "rnaseq-index", 1, 3, ["transcriptome", "annotation"],
                [("transcriptome", None, "transcriptome"), ("annotation", None, "annotation")]),
         "cpu": "4096", "memory": "16384"},
        step("quant", "rnaseq-quant", 2, 2, ["reads", "index"],
             [("reads", None, "reads"), ("index", "index", "index")]),
        DE(3, 2, [("quant", "counts", "counts")], ["quant"]),
        step("report", "bulk-report", 4, 2, ["de", "quant"],
             [("de", "de", "de"), ("quant", "counts", "counts")],
             {"REPORT_TITLE": "Bulk RNA-seq: differential expression"}),
    ]
    return {
        "name": "Bulk RNA-seq from FASTQ",
        "summary": "FASTQ to differential expression: fastp, salmon, PyDESeq2, GSEA, HTML report.",
        "description": (
            "Quantifies bulk RNA-seq libraries and tests for differential expression. Builds a salmon "
            "index from a transcriptome FASTA and GTF (rnaseq-index; build it once and keep it as a "
            "workspace reference for later runs), trims and checks reads with fastp and quantifies them "
            "with salmon, summarized to length-scaled gene counts as tximport does (rnaseq-quant), fits "
            "DESeq2 models with PyDESeq2 and runs preranked GSEA on Hallmark and GO:BP sets (bulk-de), and "
            "writes an HTML report with sample QC, PCA, volcano and MA plots and citations (bulk-report). "
            "Sample metadata comes from a samples.csv or the dataset's SPARC subjects/samples sheets; set "
            "bulk-de's DESIGN (e.g. ~ sex + condition) and CONTRASTS for your study."
            " If you used Pennsieve to store, analyse, share or publish data reported in a publication, please cite Goldblum Z, et al. Scientific Data 2025;12:1834 (doi:10.1038/s41597-025-06075-5), the datasets you used and the methods listed in the report."),
        "inputs": [
            interface("reads", "FASTQ reads", "A folder of .fastq.gz files (single- or paired-end; Illumina "
                      "names or a samples.csv), with optional SPARC samples.xlsx / subjects.xlsx.", 2),
            interface("transcriptome", "Transcriptome FASTA", "Transcript sequences, e.g. GENCODE "
                      "gencode.vM39.transcripts.fa.gz.", 3),
            interface("annotation", "Annotation GTF", "The matching GTF, e.g. gencode.vM39.annotation.gtf.gz.", 4),
        ],
        "outputs": [
            output("report_out", "Report", "report", "report", "derivatives/bulk-rnaseq/report", 5, 1),
            output("de_out", "Differential expression", "de", "de", "derivatives/bulk-rnaseq/de", 5, 2),
            output("counts_out", "Gene counts", "quant", "counts", "derivatives/bulk-rnaseq/counts", 5, 3),
        ],
        "processors": steps,
    }


def from_counts():
    steps = [
        DE(1, 2, [("counts", None, "counts")], ["counts"]),
        step("report", "bulk-report", 2, 2, ["de"], [("de", "de", "de")],
             {"REPORT_TITLE": "Bulk RNA-seq: differential expression"}),
    ]
    return {
        "name": "Bulk RNA-seq from counts",
        "summary": "Count tables to differential expression: PyDESeq2, GSEA, HTML report.",
        "description": (
            "Tests deposited bulk RNA-seq count tables for differential expression. Reads rnaseq-quant "
            "output, featureCounts, RSEM, HTSeq or STAR files, or a genes x samples CSV/TSV/XLSX, with "
            "sample metadata from a sheet or the dataset's SPARC subjects/samples (bulk-de: PyDESeq2, VST "
            "PCA, preranked GSEA on Hallmark and GO:BP), and writes an HTML report (bulk-report). Refuses "
            "TPM/FPKM tables. Set DESIGN and CONTRASTS for your study."
            " If you used Pennsieve to store, analyse, share or publish data reported in a publication, please cite Goldblum Z, et al. Scientific Data 2025;12:1834 (doi:10.1038/s41597-025-06075-5), the datasets you used and the methods listed in the report."),
        "inputs": [
            interface("counts", "Count tables", "Gene count tables plus a samples.csv or SPARC "
                      "samples.xlsx / subjects.xlsx.", 2),
        ],
        "outputs": [
            output("report_out", "Report", "report", "report", "derivatives/bulk-rnaseq/report", 3, 1),
            output("de_out", "Differential expression", "de", "de", "derivatives/bulk-rnaseq/de", 3, 2),
        ],
        "processors": steps,
    }


def main():
    out = ROOT / "workflow"
    out.mkdir(exist_ok=True)
    for name, wf in (("bulk-rnaseq-from-fastq", from_fastq()), ("bulk-rnaseq-from-counts", from_counts())):
        assert len(wf["summary"].encode()) <= 100, (name, len(wf["summary"].encode()))
        (out / f"{name}.json").write_text(json.dumps(wf, indent=2) + "\n")
        print(f"wrote workflow/{name}.json ({len(wf['processors'])} steps)")


if __name__ == "__main__":
    main()
