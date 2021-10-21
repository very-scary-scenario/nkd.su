function warnAboutProRoulette() {
  const proRouletteLink = document.querySelector('.roulette-pro a[href]')
  if (proRouletteLink === null) return
  proRouletteLink.addEventListener('click', e => {
    e.preventDefault()
    if (confirm('are you sure? using pro roulette will deny you access to other roulettes until requests open for the next show')) {
      window.location = e.target.getAttribute('href')
    }
  })
}

document.addEventListener('DOMContentLoaded', warnAboutProRoulette)
