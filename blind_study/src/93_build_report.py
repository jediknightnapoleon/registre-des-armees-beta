"""Assemble REPORT.md from src/report_parts/{head,tail}.md, the excluded-row list and the
exported model write-ups (out/model_*.md from 91_export_final.py)."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, "src", "report_parts")
OUT = os.path.join(ROOT, "out")

head = open(os.path.join(P, "head.md")).read()
tail = open(os.path.join(P, "tail.md")).read()
head = head.replace("EXCLUDED_TABLE", open(os.path.join(OUT, "excluded_rows.md")).read())

models = []
for sec, name, title in [("4.3", "13c", "best"), ("4.4", "18a", "compact"),
                         ("4.5", "18b", "simplest")]:
    body = open(os.path.join(OUT, f"model_{name}.md")).read()
    body = body.replace(f"## Model {name}\n", "")
    models.append(f"### {sec} Model {name} ({title}) — written out in full\n{body}")
intro = ("All three models use the same terms per type; the coefficients differ because each was "
         "fitted with its own army tables. Coefficients apply to the clamped x; `[flag]` means "
         "1 if the flag is true. Commander coefficients: `a` and `a_star{s}` multiply p_reg; "
         "`b{s}` and `p_army` are in gold before the ×10/N divisor. CSV copies of every table "
         "are in `out/model_<name>_*.csv`.\n\n")
report = head.replace("MODELS_PLACEHOLDER", intro + "\n".join(models)) + "\n" + tail
open(os.path.join(ROOT, "REPORT.md"), "w").write(report)
print("REPORT.md lines:", report.count("\n"))
