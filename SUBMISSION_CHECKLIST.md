# Submission Checklist

Use this before you hit submit. Each box is something the rubric explicitly grades.

## 0. Replace placeholders

Do this **first**. There are two placeholder strings in the source files:

- `Aqib Bin Qamar`
- `BSCS23178`

Files that contain them:

| File                            | Placeholders                              |
|---------------------------------|-------------------------------------------|
| `README.md`                     | `Aqib Bin Qamar`, `BSCS23178`                |
| `app/main.py`                   | `BSCS23178` (the `STUDENT_ID` constant)   |
| `report/report.md`              | `Aqib Bin Qamar`, `BSCS23178`                |
| `report/report.tex`             | `Aqib Bin Qamar`, `BSCS23178`                |

Run this from inside the repo folder (PowerShell):

```powershell
Get-ChildItem -Recurse -File -Include *.md,*.tex,*.py | ForEach-Object {
  (Get-Content $_.FullName -Raw) `
    -replace '\[YOUR-NAME\]','Your Full Name' `
    -replace '\[YOUR-ID\]','12345' |
    Set-Content -Encoding UTF8 $_.FullName
}
```

Then rename the repo folder to match the assignment's strict naming rule
(`PDC-Sp26-<ID>-<LastName>`). From the parent directory:

```powershell
Rename-Item -LiteralPath 'PDC-Sp26-STUDENTID-LASTNAME' -NewName 'PDC-Sp26-12345-Smith'
```

## 1. Hard rules from the assignment

- [ ] Repo is named exactly `PDC-Sp26-<ID>-<LastName>`.
- [ ] First line of `README.md` is `<Name> - <Student ID>`.
- [ ] Every API response carries header `X-Student-ID: <ID>`. (Verify with
      `curl -i http://127.0.0.1:8000/`.)
- [ ] PDF report is **at most 3 pages**.

## 2. Part 1 + Part 2 (the PDF)

- [ ] Generate PDF from either `report/report.md` or `report/report.tex`.
  - LaTeX (recommended): upload `report.tex` to Overleaf and click Recompile,
    or run `pdflatex report.tex` locally.
  - Markdown: `pandoc report/report.md -o report.pdf` (needs Pandoc + a
    LaTeX engine like MiKTeX/TeX Live).
- [ ] Confirm the resulting PDF is 3 pages or fewer.

## 3. Part 3 (code + tests)

- [ ] `pip install -r requirements.txt` succeeds in a fresh venv.
- [ ] `pytest -v` -> 5 tests pass.
- [ ] `uvicorn app.main:app --reload` starts without errors.
- [ ] `python scripts/demo.py` runs end-to-end against the running server.

## 4. Demo video (2 min max)

Suggested script -- aim for 1:30, hard-cap at 2:00:

1. **(0:00-0:10)** Show the README first line and the assignment problem
   you picked (Problem 3, Fault Tolerance).
2. **(0:10-0:25)** Run `curl -i http://127.0.0.1:8000/` and highlight the
   `X-Student-ID` header in the response.
3. **(0:25-0:55)** *Before*: show `POST /admin/crash-llm`, then hit
   `POST /naive/llm` once or twice -- watch it hang / 500. This is the bug.
4. **(0:55-1:35)** *After*: hit `POST /resilient/llm` six times. The first
   ~3 hit the timeout and fall back; the breaker opens; the rest return
   instantly. Show `GET /circuit/state` flipping to `OPEN`.
5. **(1:35-2:00)** Call `/admin/heal-llm`, wait 6s, hit `/resilient/llm`
   one more time -- it's fast and `state` is back to `CLOSED`.

The included `scripts/demo.py` does steps 2-5 in one go, so you can just
narrate over its output.

Upload as MP4, or as an unlisted YouTube / Loom link.

## 5. What you submit on the classroom

- [ ] **PDF report** (Part 1 + Part 2).
- [ ] **GitHub repo link** pasted into the submission box.
- [ ] **Demo video** (MP4 attachment OR unlisted YouTube/Loom URL).

That's it. Good luck.
