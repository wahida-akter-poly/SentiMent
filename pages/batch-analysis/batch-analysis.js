document.addEventListener("DOMContentLoaded", () => {
  const fileInput = document.getElementById("csvFile");
  const fileName = document.getElementById("fileName");
  const fileMeta = document.getElementById("fileMeta");
  const submit = document.getElementById("analyzeBatch");
  const status = document.getElementById("batchStatus");
  const summary = document.getElementById("resultSummary");
  const errorsNode = document.getElementById("batchErrors");
  const resultsBody = document.getElementById("batchResultsBody");
  let selectedFile = null;

  function parseCsv(text) {
    const rows = [];
    let row = [];
    let field = "";
    let quoted = false;
    for (let index = 0; index < text.length; index += 1) {
      const character = text[index];
      if (character === '"' && quoted && text[index + 1] === '"') {
        field += '"';
        index += 1;
      } else if (character === '"') {
        quoted = !quoted;
      } else if (character === "," && !quoted) {
        row.push(field);
        field = "";
      } else if ((character === "\n" || character === "\r") && !quoted) {
        if (character === "\r" && text[index + 1] === "\n") index += 1;
        row.push(field);
        if (row.some((value) => value.trim())) rows.push(row);
        row = [];
        field = "";
      } else {
        field += character;
      }
    }
    if (quoted) throw new Error("The CSV contains an unclosed quoted field.");
    row.push(field);
    if (row.some((value) => value.trim())) rows.push(row);
    return rows;
  }

  function csvItems(rows) {
    if (rows.length < 2) throw new Error("The CSV must contain a header and at least one review row.");
    const headers = rows[0].map((value) => value.trim().replace(/^\uFEFF/, "").toLowerCase());
    const reviewIndex = headers.findIndex((value) => ["review", "text", "feedback"].includes(value));
    const sourceIndex = headers.indexOf("source");
    if (reviewIndex < 0) throw new Error("Required CSV column not found. Add a Review header.");
    return rows.slice(1).map((values, index) => ({
      rowNumber: index + 2,
      text: (values[reviewIndex] || "").trim(),
      source: sourceIndex < 0 ? "csv-upload" : (values[sourceIndex] || "csv-upload").trim(),
      })).filter((item) => item.text).map((item) => {
        if (item.text.length > 5000) throw new Error(`CSV row ${item.rowNumber} exceeds 5000 characters.`);
        return item;
      });
  }

  fileInput.addEventListener("change", () => {
    selectedFile = fileInput.files?.[0] || null;
    errorsNode.textContent = "";
    if (!selectedFile) {
      fileName.textContent = "Select a CSV file";
      fileMeta.textContent = "Rows are analyzed in groups of up to 50.";
      submit.disabled = true;
      status.textContent = "No file selected";
      return;
    }
    fileName.textContent = selectedFile.name;
    fileMeta.textContent = `${(selectedFile.size / 1024).toFixed(1)} KB`;
    submit.disabled = false;
    status.textContent = "Ready to analyze";
  });

  document.getElementById("downloadTemplate").addEventListener("click", () => {
    const url = URL.createObjectURL(new Blob(["Review,Source\r\n"], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "senti-mind-template.csv";
    link.click();
    URL.revokeObjectURL(url);
  });

  submit.addEventListener("click", async () => {
    if (!selectedFile) return;
    submit.disabled = true;
    status.textContent = "Reading CSV…";
    errorsNode.textContent = "";
    resultsBody.innerHTML = '<tr><td colspan="4" class="data-empty">Analyzing rows…</td></tr>';
    try {
      const rows = parseCsv(await selectedFile.text());
      const items = csvItems(rows);
      if (!items.length) throw new Error("No non-empty review rows were found.");
      const saved = [];
      const failures = [];
      for (let offset = 0; offset < items.length; offset += 50) {
        status.textContent = `Analyzing ${Math.min(offset + 50, items.length)} of ${items.length}…`;
        const batchItems = items.slice(offset, offset + 50);
        const response = await fetch("/api/batch/analyze", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ items: batchItems.map(({ text, source }) => ({ text, source })) }),
        });
        const body = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(body.detail?.message || body.detail || "Batch analysis failed.");
        saved.push(...body.items);
        body.errors.forEach((error) => {
          const sourceRow = batchItems[error.index - 1]?.rowNumber ?? offset + error.index + 1;
          failures.push(`CSV row ${sourceRow}: ${error.error}`);
        });
      }
      summary.textContent = `${saved.length} saved; ${failures.length} skipped.`;
      status.textContent = "Import finished";
      errorsNode.textContent = failures.join("\n");
      resultsBody.innerHTML = saved.length ? "" : '<tr><td colspan="4" class="data-empty">No rows were analyzed.</td></tr>';
      saved.forEach((item) => {
        const row = document.createElement("tr");
        [item.text, item.source || "—", item.sentiment, `${(item.confidence * 100).toFixed(1)}%`].forEach((value) => {
          const cell = document.createElement("td");
          cell.textContent = value;
          row.appendChild(cell);
        });
        resultsBody.appendChild(row);
      });
    } catch (error) {
      status.textContent = "Import failed";
      summary.textContent = "No results were imported.";
      errorsNode.textContent = error.message || "Unable to read this CSV.";
      resultsBody.innerHTML = '<tr><td colspan="4" class="data-empty">Unable to process this file.</td></tr>';
    } finally {
      submit.disabled = false;
    }
  });
});
