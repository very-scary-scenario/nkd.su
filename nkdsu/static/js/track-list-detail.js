document.addEventListener('DOMContentLoaded', () => {
  const iconField = document.getElementById('id_icon')
  const iconOptionsElement = document.getElementById('icon-options')

  if (iconField === null || iconOptionsElement === null) {
    console.info('not a modifiable track list')
    return
  }

  const EMOJI = JSON.parse(iconOptionsElement.innerText.replaceAll('&quot;', '"'))

  const datalistId = 'icon-suggesstions'
  const datalist = document.createElement('datalist')
  datalist.setAttribute('id', datalistId)

  const BACKMAPPING = {}

  for (const emoji in EMOJI) {
    const option = document.createElement('option')
    const description = `${emoji} - ${EMOJI[emoji]}`
    option.setAttribute('value', description)
    BACKMAPPING[description] = emoji
    datalist.appendChild(option)
  }

  document.body.appendChild(datalist)
  iconField.setAttribute('list', datalistId)

  const backmap = ev => {
    const replacement = BACKMAPPING[iconField.value]
    if (replacement) {
      iconField.value = replacement
    }
  }

  iconField.addEventListener('input', backmap)
})
