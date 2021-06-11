let trackElements = document.querySelectorAll('.track')

function bindTrackExpansion(trackElement) {
  let toggleElement = document.createElement('a')
  toggleElement.classList.add('expansion-toggle')
  toggleElement.addEventListener('click', function () {
    trackElement.classList.toggle('expanded')
  })
  trackElement.appendChild(toggleElement)
}

for (var i = 0; i < trackElements.length; i++) {
  bindTrackExpansion(trackElements[i])
}
