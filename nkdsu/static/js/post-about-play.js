function bindPostAboutPlayInputs() {
  document.querySelectorAll('.post-about-play input[type=text]').forEach(inputElement => {
    const value = inputElement.getAttribute('value')

    inputElement.addEventListener('click', event => {
      inputElement.select()
      navigator.clipboard.writeText(value).then(() => {
        console.info(`copied: ${value}`)
      })
    })
  })
}

document.addEventListener('DOMContentLoaded', bindPostAboutPlayInputs)
