function bindAllTrackExpansion() {
  const trackElements = document.querySelectorAll('.track')

  function bindTrackExpansion(trackElement) {
    const toggleElement = document.createElement('a')
    toggleElement.classList.add('expansion-toggle')
    toggleElement.addEventListener('click', () => {
      trackElement.classList.toggle('expanded')
    })
    trackElement.appendChild(toggleElement)
  }

  for (let i = 0; i < trackElements.length; i++) {
    bindTrackExpansion(trackElements[i])
  }
}

document.addEventListener('DOMContentLoaded', bindAllTrackExpansion)
