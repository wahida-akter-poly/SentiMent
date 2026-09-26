document.addEventListener("DOMContentLoaded", () => {
  const period = document.querySelector(".period-select");
  const labels = document.querySelectorAll(".mini-label");
  const setPeriodLabel = () => {
    labels.forEach((label) => {
      if (period) label.textContent = period.value;
    });
  };
  const dateValue = (value) => `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
  if (period) {
    period.addEventListener("change", setPeriodLabel);
    setPeriodLabel();
  }

  const exportButton = document.getElementById("exportButton");
  exportButton?.addEventListener("click", async () => {
    try {
      const params = new URLSearchParams();
      const selected = period?.value || "Last 30 days";
      const today = new Date();
      let start = null;
      if (selected === "Last 7 days") {
        start = new Date(today);
        start.setDate(start.getDate() - 6);
      } else if (selected === "This year") {
        start = new Date(today.getFullYear(), 0, 1);
      } else {
        start = new Date(today);
        start.setDate(start.getDate() - 29);
      }
      params.set("start", dateValue(start));
      params.set("end", dateValue(today));
      params.set("format", "csv");
      const response = await fetch(`/api/analyses/export.csv?${params.toString()}`);
      if (!response.ok) throw new Error("Unable to export CSV");
      const blob = await response.blob();
      const link = document.createElement("a");
      const url = URL.createObjectURL(blob);
      link.href = url;
      link.download = "senti_mind_analyses.csv";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      window.alert(error.message || "CSV export is unavailable.");
    }
  });

});
