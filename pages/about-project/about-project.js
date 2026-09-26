// About Project page: cards respond to keyboard focus as well as pointer navigation.
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".about-card").forEach((card) => {
    card.tabIndex = 0;
    card.addEventListener("focus", () => card.classList.add("about-card-active"));
    card.addEventListener("blur", () => card.classList.remove("about-card-active"));
  });

  const setValue = (id, value) => {
    const node = document.getElementById(id);
    if (node) node.textContent = value == null ? "Unavailable" : String(value);
  };
  fetch("/api/model/status")
    .then((response) => {
      if (!response.ok) throw new Error("Model metadata is unavailable.");
      return response.json();
    })
    .then((model) => {
      const description = document.getElementById("modelMetadataDescription");
      if (description) {
        description.textContent = model.available
          ? "Values below are read from the loaded model artifact."
          : "Model Not Trained. Train and configure a real artifact to enable inference.";
      }
      setValue("aboutModelVersion", model.model_version);
      setValue("aboutModelLabels", model.labels?.length ? model.labels.join(", ") : null);
      setValue("aboutModelAccuracy", model.accuracy == null ? null : `${(model.accuracy * 100).toFixed(1)}%`);
      setValue("aboutModelF1", model.macro_f1 == null ? null : `${(model.macro_f1 * 100).toFixed(1)}%`);
      setValue("aboutTrainRows", model.train_rows);
      setValue("aboutTestRows", model.test_rows);
    })
    .catch(() => {
      const description = document.getElementById("modelMetadataDescription");
      if (description) description.textContent = "Unable to load model metadata.";
    });
});
