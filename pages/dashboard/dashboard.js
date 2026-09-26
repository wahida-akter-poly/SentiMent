document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".kpi-card").forEach((card, index) => {
    card.style.animationDelay = `${index * 80}ms`;
    card.classList.add("kpi-ready");
  });
  fetch("/api/dashboard/summary")
    .then((response) => {
      if (!response.ok) throw new Error("Dashboard data unavailable");
      return response.json();
    })
    .then((summary) => {
      document.getElementById("totalReviews").textContent = summary.total;
      ["positive", "neutral", "negative"].forEach((label) => {
        const value = summary.percentages[label];
        const display = value == null ? "—" : `${value.toFixed(1)}%`;
        const element = document.getElementById(`${label}Percent`);
        if (element) element.textContent = display;
        const legend = document.getElementById(`dashboard${label[0].toUpperCase()}${label.slice(1)}Legend`);
        if (legend) legend.textContent = summary.counts[label];
      });
      const status = document.getElementById("dataStatus");
      if (status) status.textContent = summary.has_data ? `${summary.total} saved analyses` : "No saved analyses";
    })
    .catch(() => {
      const status = document.getElementById("dataStatus");
      if (status) status.textContent = "Data unavailable";
    });
});
