function respectHashForDarkMode() {
  if (window.location.hash === '#dark') {
    document.body.classList.add('dark');
  } else {
    document.body.classList.remove('dark');
  }
}

respectHashForDarkMode();

window.addEventListener('hashchange', respectHashForDarkMode);
