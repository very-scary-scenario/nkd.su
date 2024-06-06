function bindPostAboutPlayInputs() {
  document.querySelectorAll('.post-about-play input[type=text]').forEach(inputElement => {
    inputElement.addEventListener('click', event => {
      inputElement.select()
    })
  })
}

document.addEventListener('DOMContentLoaded', bindPostAboutPlayInputs)
