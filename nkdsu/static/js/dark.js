function bindDarkModeForm() {
  const darkModeForm = document.getElementById('dark-mode-settings');
  let lastSubmitButtonClicked;

  if (fetch !== undefined) {
    darkModeForm.addEventListener('submit', function(e) {
      const data = new FormData(darkModeForm);

      if (e.submitter) {
        data.set('mode', e.submitter.getAttribute('value'));
      } else if (lastSubmitButtonClicked) {
        // firefox doesn't set a submitter, so we cheat:
        data.set('mode', lastSubmitButtonClicked.getAttribute('value'));
      } else {
        // we couldn't work out what button was clicked; let the browser's form handling do it
        return;
      }

      e.preventDefault();

      fetch(darkModeForm.getAttribute('action'),
        {method: 'post', body: data, redirect: 'manual'})
        .then(function(response) {
          console.log(response);
        });

      document.body.setAttribute('data-dark-mode', data.get('mode'));
    });
  }

  darkModeForm.querySelectorAll('button[name=mode]').forEach(function(button) {
    button.addEventListener('click', function(e) {
      lastSubmitButtonClicked = button;
    });
  });
}

$(document).ready(bindDarkModeForm);
