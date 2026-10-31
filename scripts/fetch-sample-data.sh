#!/usr/bin/env bash
# Downloads the demo data of the bulk RNA-seq workflows into data/:
#   - Discover 427 (RE-JOIN, CC BY 4.0): 12 single-end mouse trigeminal ganglion RNA-seq libraries
#     (female/male x normal/tongue tumour, 3 pools each) with the authors' per-sample gene counts.
#     Discover files sit in a requester-pays S3 bucket: any AWS credentials work (set AWS_PROFILE).
#   - GENCODE mouse release M39 transcripts + annotation (public, no credentials), for rnaseq-index.
# Idempotent: files already present are skipped.
set -euo pipefail
cd "$(dirname "$0")/.."
API=https://api.pennsieve.io/discover
GENCODE=https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_mouse/release_M39

uri() { curl -fsS "$API/datasets/$1/versions/$2/files?path=$(python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1]))' "$3")" | python3 -c 'import json,sys;print(json.load(sys.stdin)["uri"])'; }
browse() { curl -fsS "$API/datasets/$1/versions/$2/files/browse?path=$3&limit=1000"; }
walk() {
  browse "$1" "$2" "$3" | python3 -c 'import json,sys
for f in json.load(sys.stdin).get("files", []): print(f["type"], f["path"])' | while read -r t p; do
    if [ "$t" = Directory ]; then walk "$1" "$2" "$p"; else echo "$p"; fi
  done
}
get() {
  [ -s "$4" ] && return 0
  mkdir -p "$(dirname "$4")"
  aws s3 cp --only-show-errors --request-payer requester "$(uri "$1" "$2" "$3")" "$4.part" && mv "$4.part" "$4"
}

D=data/tg-tumour
for f in files/subjects.xlsx files/samples.xlsx files/dataset_description.xlsx; do get 427 1 "$f" "$D/${f#files/}"; done
walk 427 1 files/primary | grep -E '\.(fastq\.gz|fastq\.gz\.md5|txt)$' | while read -r p; do get 427 1 "$p" "$D/${p#files/}"; done
# Check the FASTQ against the authors' md5 files.
( cd "$D/primary" && for m in */*.md5; do
    want=$(awk '{print $1}' "$m"); got=$(md5 -q "${m%.md5}" 2>/dev/null || md5sum "${m%.md5}" | awk '{print $1}')
    [ "$want" = "$got" ] || { echo "md5 mismatch: ${m%.md5}" >&2; exit 1; }
  done )

R=data/reference/gencode-mouse-M39
mkdir -p "$R"
for f in gencode.vM39.transcripts.fa.gz gencode.vM39.annotation.gtf.gz GRCm39.primary_assembly.genome.fa.gz; do
  if [ ! -s "$R/$f" ]; then curl -fsS -o "$R/$f.part" "$GENCODE/$f" && mv "$R/$f.part" "$R/$f"; fi
done
ls -la "$R"
echo done
