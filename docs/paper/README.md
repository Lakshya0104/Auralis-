# AURALIS IEEE draft

- `auralis_ieee.pdf`: the draft (IEEE conference format, IEEEtran). Orange **[brackets]** are still to be filled in or measured.
- `auralis_ieee.tex`: source. Open it in Overleaf (*New project → Upload*, together with `figures/`) or build it locally with `pdflatex auralis_ieee && pdflatex auralis_ieee`.
- `make_figures.py` and `routing_eval.mjs`: produce every figure and number in the paper from the project's own code (`results.json`, `routing.json`).

To rebuild after a change:
```bash
node docs/paper/routing_eval.mjs > docs/paper/routing.json
python docs/paper/make_figures.py
cd docs/paper && pdflatex auralis_ieee && pdflatex auralis_ieee
```

Before submitting: fill in authors, run the field experiments in Table IV, add recent related work, and check every reference against the original paper.
