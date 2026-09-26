/* Shared navigation and API-backed SENTI-MIND interactions. */
document.addEventListener("DOMContentLoaded", () => {
  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("sidebarOverlay");
  const closeMenu = () => {
    sidebar?.classList.remove("open");
    overlay?.classList.remove("open");
  };
  document.getElementById("menuToggle")?.addEventListener("click", () => {
    sidebar?.classList.toggle("open");
    overlay?.classList.toggle("open");
  });
  overlay?.addEventListener("click", closeMenu);
  document.querySelectorAll(".nav-link").forEach((link) => link.addEventListener("click", closeMenu));

  const request = async (url, options) => {
    const response = await fetch(url, options);
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw Object.assign(new Error(body.detail?.message || body.detail || "Request failed"), { status: response.status, body });
    return body;
  };
  const setText = (id, value) => {
    const node = document.getElementById(id);
    if (node) node.textContent = value;
  };
  const percent = (value) => (value == null ? "—" : `${Number(value).toFixed(1)}%`);
  const showEmpty = (canvas, message) => {
    if (!canvas) return;
    canvas.hidden = true;
    const box = canvas.parentElement;
    if (box && !box.querySelector(".data-empty")) {
      const note = document.createElement("p");
      note.className = "data-empty";
      note.textContent = message;
      box.append(note);
    }
  };
  const palette = { positive: "#24a56b", neutral: "#f3a62f", negative: "#e45d63", mixed: "#3977f6" };
  const chartDefaults = {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { display: false }, tooltip: { padding: 10, cornerRadius: 7 } },
  };

  function renderCharts(data, ids) {
    if (!data.has_data || typeof Chart === "undefined") {
      [ids.doughnut, ids.bar, ids.line].forEach((id) => showEmpty(document.getElementById(id), "No analyzed records yet."));
      return;
    }
    const doughnut = document.getElementById(ids.doughnut);
    if (doughnut) {
      doughnut.hidden = false;
      doughnut.parentElement?.querySelector(".data-empty")?.remove();
      Chart.getChart?.(doughnut)?.destroy();
      new Chart(doughnut, {
      type: "doughnut",
      data: { labels: ["Positive", "Neutral", "Negative", "Mixed"], datasets: [{ data: ["positive", "neutral", "negative", "mixed"].map((key) => data.counts[key]), backgroundColor: Object.values(palette), borderWidth: 0 }] },
      options: { ...chartDefaults, cutout: "72%" },
      });
    }
    const bar = document.getElementById(ids.bar);
    if (bar) {
      bar.hidden = false;
      bar.parentElement?.querySelector(".data-empty")?.remove();
      Chart.getChart?.(bar)?.destroy();
      new Chart(bar, {
      type: "bar",
      data: { labels: data.by_source.map((row) => row.source), datasets: [{ label: "Analyzed records", data: data.by_source.map((row) => row.count), backgroundColor: "#6d9af8", borderRadius: 5, borderSkipped: false }] },
      options: { ...chartDefaults, scales: { x: { grid: { display: false } }, y: { beginAtZero: true, ticks: { precision: 0 } } } },
      });
    }
    const line = document.getElementById(ids.line);
    if (line) {
      line.hidden = false;
      line.parentElement?.querySelector(".data-empty")?.remove();
      Chart.getChart?.(line)?.destroy();
      new Chart(line, {
      type: "line",
      data: { labels: data.trend.map((row) => row.date), datasets: ["positive", "neutral", "negative", "mixed"].map((key) => ({ label: key, data: data.trend.map((row) => row[key]), borderColor: palette[key], backgroundColor: `${palette[key]}18`, fill: key === "positive", tension: 0.35, pointRadius: 3, borderWidth: 2 })) },
      options: { ...chartDefaults, interaction: { mode: "index", intersect: false }, scales: { x: { grid: { display: false } }, y: { beginAtZero: true, ticks: { precision: 0 } } } },
      });
    }
  }

  async function loadSummary() {
    const isAnalytics = Boolean(document.getElementById("analyticsDoughnut"));
    const endpoint = isAnalytics ? "/api/analytics/summary" : "/api/dashboard/summary";
    try {
      const params = new URLSearchParams();
      if (isAnalytics) {
        const period = document.querySelector(".period-select")?.value || "Last 30 days";
        const today = new Date();
        const start = new Date(today);
        if (period === "This year") start.setFullYear(today.getFullYear(), 0, 1);
        else start.setDate(today.getDate() - (period === "Last 7 days" ? 6 : 29));
        params.set("start", `${start.getFullYear()}-${String(start.getMonth() + 1).padStart(2, "0")}-${String(start.getDate()).padStart(2, "0")}`);
        params.set("end", `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`);
      }
      const data = await request(`${endpoint}${params.size ? `?${params.toString()}` : ""}`);
      setText("dataStatus", data.has_data ? `${data.total} records` : "No records yet");
      setText("totalReviews", data.total.toLocaleString());
      setText("positivePercent", percent(data.percentages.positive));
      setText("neutralPercent", percent(data.percentages.neutral));
      setText("negativePercent", percent(data.percentages.negative));
      setText("mixedPercent", percent(data.percentages.mixed));
      setText("dashboardPositiveLegend", data.counts.positive.toLocaleString());
      setText("dashboardNeutralLegend", data.counts.neutral.toLocaleString());
      setText("dashboardNegativeLegend", data.counts.negative.toLocaleString());
      setText("dashboardMixedLegend", data.counts.mixed.toLocaleString());
      setText("averageConfidence", data.average_confidence == null ? "—" : `${(data.average_confidence * 100).toFixed(1)}%`);
      setText("analyzedItems", data.total.toLocaleString());
      setText("analyticsPositive", data.counts.positive.toLocaleString());
      setText("analyticsNeutral", data.counts.neutral.toLocaleString());
      setText("analyticsNegative", data.counts.negative.toLocaleString());
      setText("analyticsMixed", data.counts.mixed.toLocaleString());
      setText("sourceCount", data.by_source.length.toLocaleString());
      setText("leadSource", data.by_source[0]?.source || "—");
      const renderRanking = (id, rows, label) => {
        const list = document.getElementById(id);
        if (!list) return;
        list.replaceChildren();
        if (!rows?.length) {
          const item = document.createElement("li");
          item.className = "data-empty";
          item.textContent = `No ${label} data yet.`;
          list.append(item);
          return;
        }
        rows.forEach((row) => {
          const item = document.createElement("li");
          item.textContent = `${row.name} (${row.count})`;
          list.append(item);
        });
      };
      renderRanking(isAnalytics ? "analyticsTopAspects" : "dashboardTopAspects", data.top_aspects, "aspect");
      renderRanking(isAnalytics ? "analyticsTopTopics" : "dashboardTopTopics", data.top_topics, "topic");
      renderRanking(isAnalytics ? "analyticsTopComplaints" : "dashboardTopComplaints", data.top_complaints, "complaint");
      renderCharts(data, isAnalytics ? { doughnut: "analyticsDoughnut", bar: "analyticsBar", line: "analyticsLine" } : { doughnut: "distributionChart", bar: "platformChart", line: "trendChart" });
      if (!data.has_data) document.querySelectorAll(".table-panel tbody").forEach((body) => (body.innerHTML = '<tr><td colspan="5" class="data-empty">No analyzed records yet.</td></tr>'));
    } catch (error) {
      setText("dataStatus", "Data unavailable");
      document.querySelectorAll(".data-empty").forEach((node) => (node.textContent = "Unable to load analytics data."));
    }
  }
  if (document.getElementById("distributionChart") || document.getElementById("analyticsDoughnut")) {
    loadSummary();
    if (document.getElementById("analyticsDoughnut")) {
      document.querySelector(".period-select")?.addEventListener("change", loadSummary);
    }
  }

  async function loadRecent() {
    const body = document.getElementById("recentAnalysisBody");
    if (!body) return;
    try {
      const data = await request("/api/analyses?limit=25");
      body.innerHTML = "";
      if (!data.items.length) {
        body.innerHTML = '<tr><td colspan="4" class="data-empty">No analyzed records yet.</td></tr>';
        return;
      }
      data.items.forEach((item) => {
        const row = document.createElement("tr");
        const review = document.createElement("td");
        review.textContent = `${item.text.slice(0, 80)}${item.text.length > 80 ? "…" : ""}`;
        const source = document.createElement("td");
        source.textContent = item.source || "manual";
        const sentiment = document.createElement("td");
        sentiment.innerHTML = `<span class="sentiment-tag ${item.sentiment}">${item.sentiment}</span>`;
        const confidence = document.createElement("td");
        confidence.textContent = `${(item.confidence * 100).toFixed(1)}%`;
        const time = document.createElement("td");
        time.textContent = new Date(item.created_at).toLocaleString();
        row.append(review, source, sentiment, confidence, time); body.append(row);
      });
    } catch (_) {
      body.innerHTML = '<tr><td colspan="4" class="data-empty">Unable to load analysis history.</td></tr>';
    }
  }

  document.getElementById("clearRecent")?.addEventListener("click", loadRecent);
  if (document.getElementById("recentAnalysisBody")) loadRecent();
  request("/api/model/status").then((status) => document.querySelectorAll(".model-status").forEach((node) => {
    node.textContent = status.available ? "Model Ready" : "Model Not Trained";
  })).catch(() => {});
});
