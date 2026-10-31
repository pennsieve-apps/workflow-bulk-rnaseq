# Conventions shared by the bulk RNA-seq apps

Workflows:

- **A. Bulk RNA-seq from FASTQ:** `rnaseq-quant (+ index) → bulk-de → bulk-report`
- **B. Bulk RNA-seq from counts:** `bulk-de → bulk-report` (count tables from a dataset: our own
  `gene_counts.csv`, featureCounts, RSEM `*.genes.results`, HTSeq, STAR `ReadsPerGene.out.tab`,
  or a genes × samples CSV/TSV/XLSX as deposited)
- **Reference build (once per genome, kept as a workspace reference):** `rnaseq-index`

## Runtime contract

As the single-cell suite (`~/code/pennsieve/workflow-single-cell/docs/conventions.md`,
"Runtime contract"): `$INPUT_DIR`/`$OUTPUT_DIR`, env parameters, one output = whole
`$OUTPUT_DIR`, 2+ = `$OUTPUT_DIR/<name>/`, `placement: subfolder` for multi-input apps that
also work with everything merged at the root, `LABEL` folders for apps that can run more than
once (bulk-de per contrast set), port names without underscores, `provenance.json` with
`citations`, per-sample failure tolerance, exit codes 1/2, `THREADS`, `SEED`, **no network at
run time**, non-root containers, untrusted inputs (path checks, no unsafe deserialisation), no
clinical values in logs. The **Credits** section of that file applies unchanged: every
reference verified against Crossref/PubMed/DataCite/Discover and the project's LICENSE.

## Files

### Index (`index` port of rnaseq-index, input of rnaseq-quant)

A folder: `salmon/` (the salmon index, built with the genome as decoys when a genome FASTA is
given, `-k 31`), `tx2gene.csv` (`transcript_id, gene_id, gene_name, gene_type`; versions kept
as in the FASTA headers), `genes.csv` (`gene_id, gene_name, gene_type, chrom, length`),
`index.json` (`organism`, `source` (e.g. `GENCODE M39`), file names and sha256 of the inputs,
salmon version, decoys yes/no). rnaseq-quant refuses an index whose salmon major version
differs from its own.

### Reads (`reads` input of rnaseq-quant)

FASTQ (`.fastq.gz`, `.fq.gz`, plain also accepted) anywhere under the input. Samples are
grouped by name: Illumina `<sample>_S<n>_L<lane>_R<1|2>_001`, `<sample>_R1/_R2`, `_1/_2`;
lanes of one sample are concatenated logically (salmon takes several files). Paired when every
R1 has an R2. An optional sample sheet (`SAMPLE_SHEET`, default `samples.csv`: `sample_id`,
`fastq_1`, `fastq_2` (optional), then any metadata) overrides the grouping. SPARC
`samples.xlsx`/`subjects.xlsx` are read as in sc-prep (same matching on `sam-`/`sub-`/`pool-`
folders, same `METADATA_COLUMNS` allow-list, `samples_full.csv` for everything).

### Counts (`counts` port of rnaseq-quant; input of bulk-de)

- `gene_counts.csv`: `gene_id, gene_name`, then one column per `sample_id`; estimated counts
  summed per gene, **length-scaled** (tximport `countsFromAbundance="lengthScaledTPM"`), rounded
  to integers, so DESeq2 needs no offsets.
- `gene_tpm.csv`: same shape, TPM.
- `samples.csv`: `sample_id`, `files` (relative paths, `;`-separated), `layout` (`single`,
  `paired`), `reads_in`, `reads_after_trim`, `mapping_rate`, `library_type` (salmon's), then
  metadata columns.
- `qc/`: per sample `<sample_id>.fastp.json`, `<sample_id>.fastp.html`, salmon `meta_info.json`
  and `lib_format_counts.json` copied as `<sample_id>.salmon.json`.

bulk-de reads either this or the other count formats above (it converts them to the same
`gene_counts.csv` + `samples.csv` shape and says what it found in `de.json`).

### Differential expression (`de` port of bulk-de)

Under `<LABEL>/`: `design.json` (formula, contrasts, reference levels, samples used, genes
filtered), `pca.csv` + `pca.png` (VST), `<contrast>.csv` per contrast (`gene_id, gene_name,
base_mean, log2_fold_change, lfc_se, stat, pvalue, padj`, shrunk LFC in `log2_fold_change_shrunk`
when available), `<contrast>_volcano.png`, `<contrast>_ma.png`, `<contrast>_gsea.csv` (preranked
by `stat`), `summary.json` (per contrast: n up/down at `FDR`, top genes).

Contrasts are written `<column>:<level>:<reference>` (e.g. `condition:tumour:normal`); the
contrast's file name is `<column>-<level>-vs-<reference>`.

### Tables and figures

As in the single-cell suite.

## Demo data

Under `~/code/pennsieve/workflow-bulk-rnaseq/data/` (gitignored; `scripts/fetch-sample-data.sh`):

- `tg-tumour/`: Discover 427 v1, *Sex-dependent differences in the genomic profile of lingual
  sensory neurons in naïve and tongue-tumor bearing mice* (RE-JOIN; Tumanov A, Shein S, Lai Z,
  Chen Y, Ruparel S; doi:10.26275/gaap-zlpj; CC BY 4.0; described by
  doi:10.1038/s41598-023-40380-6). 12 single-end libraries `primary/pool-<F|M><N|T><1-3>/` with
  `*_R1.fastq.gz` (~1 GB each), the authors' per-sample `*_Genes_ReadCount.txt`, and SPARC
  `samples.xlsx`/`subjects.xlsx`. Design: sex (F/M) × condition (N = naïve, T = tongue tumour).
  The authors' counts let bulk-de be tested without quantification and let rnaseq-quant be
  compared against them (gene-level correlation).
- `reference/gencode-mouse-M39/`: GENCODE mouse release M39 `gencode.vM39.transcripts.fa.gz`,
  `gencode.vM39.annotation.gtf.gz`, `GRCm39.primary_assembly.genome.fa.gz` (Frankish A, et al.
  GENCODE 2023, doi:10.1093/nar/gkac1071; verify).

Local Docker has 8 GB shared with other builders: test rnaseq-quant on reads subsampled to 1 M
per sample (`seqtk sample -s42`, write them under `data/work/`), and say what full-size runs need.
