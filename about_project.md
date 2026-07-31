# About this project

SPINDEP is the analysis codebase for my M.Sc. thesis at the University of Ibadan, supervised by Prof. O.E. Oyewande. The thesis itself asks whether spin-dependent exotic interactions couple differently to matter and antimatter — a possible CPT-violation signature — by mapping Standard Model Extension coefficients onto the Dobrescu–Mocioiu potential catalogue and comparing published experimental bounds across the two sectors. This repo is the tool I wrote to actually do that comparison at scale instead of doing it pair by pair in a spreadsheet.

It started as a single `main.py` script that read a folder of CSVs and printed a chi-squared number. That's still roughly what it does at its core — discover datasets, match matter to antimatter, interpolate onto a shared λ grid, compute the asymmetry parameter A_α, run a significance test — but it's since grown a proper CLI (`spin`), a web GUI for browsing results without touching the terminal, and enough dataset-handling machinery to cope with the naming inconsistencies across ~270 constraint files pulled from a few decades of papers.

For how to actually install and run it, see [README.md](README.md) — that's the up-to-date reference. This file is just the "why does this exist" version.

## Why a whole framework instead of doing it by hand

Two reasons, mainly. First, the matter/antimatter comparison is the same four or five steps every time — parse, match, interpolate, compute A_α, check significance — and doing that by hand for ~14+ valid pairs across multiple couplings (gAgA, gsgs, gVgV, gpgp...) gets error-prone fast, especially with unit conversions between the different λ conventions papers use (metres, eV⁻¹, MeV⁻¹, ...). Second, once it's automated, it's trivial to re-run the whole database whenever a new constraint paper comes out, which matters for a field that's moving as quickly as this one currently is.

## Where the physics content lives

The actual derivations — the Foldy–Wouthuysen reduction of the SME coefficients, the matching onto Dobrescu–Mocioiu potentials, the caveats about what A_α can and can't tell you when the inputs are one-sided experimental bounds rather than signed measurements — live in the thesis repo (`exotic-spin-interactions-SME`), not here. This repo is deliberately just the computational/statistical layer on top of that.

## Status

Working and used for the actual thesis results, but still a solo research tool rather than a polished package — expect some rough edges (a few legacy scripts under `spindep/src/` predate the current CLI and are kept around for reference rather than active use).
