document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("analysisText");
  const analyze = document.getElementById("analyzeButton");
  const count = document.getElementById("characterCount");
  const empty = document.getElementById("emptyResult");
  const result = document.getElementById("analysisResult");
  if (!input || !analyze || !count) return;

  const setText = (id, value) => {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
  };
  const percent = (value) => value == null ? "Not measured" : `${(value * 100).toFixed(1)}%`;
  const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (character) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]
  );
  const refreshHistory = async () => {
    const params = new URLSearchParams({ limit: "10" });
    const filters = {
      q: document.getElementById("historyQuery")?.value.trim(),
      source: document.getElementById("historySource")?.value.trim(),
      sentiment: document.getElementById("historySentiment")?.value,
      start: document.getElementById("historyStart")?.value,
      end: document.getElementById("historyEnd")?.value,
    };
    Object.entries(filters).forEach(([key, value]) => value && params.set(key, value));
    const response = await fetch(`/api/analyses?${params.toString()}`);
    if (!response.ok) throw new Error("Unable to load analysis history.");
    const body = await response.json();
    const table = document.getElementById("recentAnalysisBody");
    if (!table) return;
    table.innerHTML = body.items.length ? body.items.map((item) =>
      `<tr><td>${escapeHtml(item.text)}</td><td>${escapeHtml(item.sentiment)}</td>` +
      `<td>${percent(item.confidence)}</td><td>${new Date(item.created_at).toLocaleString()}</td></tr>`
    ).join("") : '<tr><td colspan="4" class="data-empty">No matching analyses.</td></tr>';
  };

  input.addEventListener("input", () => {
    count.textContent = `${input.value.length} / ${input.maxLength} characters`;
  });
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      analyze.click();
    }
  });
  analyze.addEventListener("click", async () => {
    const text = input.value.trim();
    if (!text) {
      empty.classList.remove("hidden");
      const messageNode = empty.querySelector("p");
      if (messageNode) messageNode.textContent = "Please enter feedback before analyzing.";
      result.classList.add("hidden");
      input.focus();
      return;
    }
    if (text.length > 5000) {
      empty.classList.remove("hidden");
      const messageNode = empty.querySelector("p");
      if (messageNode) messageNode.textContent = "Text must be 5000 characters or fewer.";
      result.classList.add("hidden");
      return;
    }
    analyze.disabled = true;
    analyze.textContent = "Analyzing…";
    try {
      const response = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, source: document.getElementById("sourceTag")?.value.trim() || null }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail?.message || body.detail || "Analysis failed.");
      empty.classList.add("hidden");
      result.classList.remove("hidden");
      setText("resultSentiment", body.sentiment);
      setText("modelSentiment", body.model_sentiment);
      setText("summaryText", body.summary_text || "Not available");
      setText("confidenceScore", percent(body.confidence));
      setText("resultDescription", `Model ${body.model_version} · ${new Date(body.created_at).toLocaleString()}`);
      const confidenceBar = document.getElementById("confidenceBar");
      if (confidenceBar) confidenceBar.style.width = `${body.confidence * 100}%`;
      ["positive", "neutral", "negative"].forEach((label) => {
        const value = body.probabilities[label];
        setText(`${label}Probability`, percent(value));
        const bar = document.getElementById(`${label}Bar`);
        if (bar) bar.style.width = value == null ? "0%" : `${value * 100}%`;
      });
      const sentenceList = document.getElementById("sentenceResults");
      sentenceList.replaceChildren(...(body.sentence_results || []).map((sentence) => {
        const item = document.createElement("li");
        item.textContent = `${sentence.sentiment}: ${sentence.text} (${percent(sentence.confidence)})`;
        return item;
      }));
      const aspectList = document.getElementById("aspectResults");
      aspectList.replaceChildren(...(body.aspects || []).map((aspect) => {
        const item = document.createElement("li");
        item.textContent = `${aspect.aspect}: ${aspect.sentiment} · ${aspect.evidence}`;
        return item;
      }));
      setText("topicResults", (body.topics || []).join(", ") || "No topics extracted");
      const evidence = body.evidence || {};
      setText("evidenceResults", [evidence.strongest_positive, evidence.strongest_negative]
        .filter(Boolean).map((item) => item.text).join(" | ") || "No positive or negative evidence");
      await refreshHistory();
    } catch (error) {
      empty.classList.remove("hidden");
      const messageNode = empty.querySelector("p");
      if (messageNode) messageNode.textContent = error.message;
      result.classList.add("hidden");
    } finally {
      analyze.disabled = false;
      analyze.textContent = "⌁ Analyze Sentiment";
    }
  });
  document.getElementById("historyFilters")?.addEventListener("submit", (event) => {
    event.preventDefault();
    refreshHistory().catch(() => {});
  });
  document.getElementById("resetHistoryFilters")?.addEventListener("click", () => {
    window.setTimeout(() => refreshHistory().catch(() => {}), 0);
  });
  refreshHistory().catch(() => {});
});
