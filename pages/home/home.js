// Home page: reveal navigation cards as visitors explore the workspace.
document.addEventListener("DOMContentLoaded", () => {
  const cards = document.querySelectorAll(".destination-card");
  if (!("IntersectionObserver" in window)) return;
  const observer = new IntersectionObserver(
    (entries) => entries.forEach((entry) => entry.isIntersecting && entry.target.classList.add("is-visible")),
    { threshold: 0.15 },
  );
  cards.forEach((card) => observer.observe(card));

  fetch("/api/dashboard/summary")
    .then((response) => response.json())
    .then((data) => {
      if (!data.has_data) return;
      ["positive", "neutral", "negative"].forEach((label) => {
        const value = data.percentages[label] == null ? "—" : `${Number(data.percentages[label]).toFixed(1)}%`;
        const bar = document.querySelector(`.${label}-bar`);
        if (bar) bar.style.width = `${data.percentages[label] || 0}%`;
        const node = document.getElementById(`home${label[0].toUpperCase()}${label.slice(1)}Bar`);
        if (node) node.textContent = value;
      });
      const positive = document.getElementById("homePositive");
      if (positive) positive.textContent = `${Number(data.percentages.positive).toFixed(1)}%`;
      if (positive) positive.nextElementSibling.textContent = "positive";
    })
    .catch(() => {});
});
