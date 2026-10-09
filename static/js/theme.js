// Light/dark toggle shared by the Checkbox pages.
// Loaded in <head>, so the saved theme applies before the page draws.
try {
  if (localStorage.getItem("theme")) {
    document.documentElement.dataset.theme = localStorage.getItem("theme");
  }
} catch (e) {}

function currentTheme() {
  return document.documentElement.dataset.theme ||
         (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
}

function showThemeButton() {
  var button = document.getElementById("theme");
  if (button) {
    button.textContent = currentTheme() == "dark" ? "\u2600 Light" : "\u263E Dark";
  }
}

function toggleTheme() {
  var theme = currentTheme() == "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = theme;
  try {
    localStorage.setItem("theme", theme);
  } catch (e) {}
  showThemeButton();
}

document.addEventListener("DOMContentLoaded", showThemeButton);
