function showHome() {

  document.getElementById("homePage")
    .classList.add("active-page");

  document.getElementById("dashboardPage")
    .classList.remove("active-page");

  document.getElementById("homeNav")
    .classList.add("active");

  document.getElementById("dashboardNav")
    .classList.remove("active");

  window.scrollTo(0, 0);
}

function showDashboard() {

  document.getElementById("homePage")
    .classList.remove("active-page");

  document.getElementById("dashboardPage")
    .classList.add("active-page");

  document.getElementById("homeNav")
    .classList.remove("active");

  document.getElementById("dashboardNav")
    .classList.add("active");

  window.scrollTo(0, 0);
}

function selectMode(mode) {

  document.getElementById("imageOption")
    .classList.toggle(
      "selected",
      mode === "image"
    );

  document.getElementById("videoOption")
    .classList.toggle(
      "selected",
      mode === "video"
    );

  document.getElementById("imageUpload")
    .style.display =
    mode === "image"
      ? "block"
      : "none";

  document.getElementById("videoUpload")
    .style.display =
    mode === "video"
      ? "block"
      : "none";
}

document.getElementById("imageInput")
  .addEventListener("change", function () {

    document.getElementById("imageFileName")
      .textContent =
      this.files[0]
        ? this.files[0].name
        : "No image selected";

  });

document.getElementById("videoInput")
  .addEventListener("change", function () {

    document.getElementById("videoFileName")
      .textContent =
      this.files[0]
        ? this.files[0].name
        : "No video selected";

  });
