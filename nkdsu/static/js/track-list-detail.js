/* global Sortable */

const bindIconOptions = () => {
  const iconField = document.getElementById('id_icon')
  const iconOptionsElement = document.getElementById('icon-options')

  if (iconField === null || iconOptionsElement === null) {
    return
  }

  const EMOJI = JSON.parse(iconOptionsElement.innerText.replaceAll('&quot;', '"').replaceAll('&amp;', '&'))

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
}

const bindMembershipForm = () => {
  const HANDLE_CLASS = 'handle'
  const HANDLE_TITLE = 'grab handle'

  const membershipForm = document.getElementById('track-list-membership-form')
  const membershipContainer = document.getElementById('track-list-membership')

  if (membershipForm === null || membershipContainer === null || membershipForm.querySelector('input[type=submit]') === null) {
    return
  }

  const getOrderInputs = () => membershipContainer.querySelectorAll('input.order')

  membershipContainer.querySelectorAll('.track-list-membership-controls').forEach(membershipControls => {
    const handle = document.createElement('span')
    handle.classList.add(HANDLE_CLASS)
    handle.title = HANDLE_TITLE
    membershipControls.prepend(handle)
  })

  const normalise = e => {
    const orderInputs = getOrderInputs()
    for (let i = 0; i < orderInputs.length; i++) {
      const orderInput = orderInputs[i]
      orderInput.value = i + 1
      orderInput.oldValue = orderInput.value
    }
  }

  const sortable = Sortable.create(membershipContainer, {
    onSort: normalise,
    handle: `.${HANDLE_CLASS}`,
  })

  const orderingTutorial = document.createElement('p')
  const handlePlaceholder = document.createElement('span')
  handlePlaceholder.classList.add(`${HANDLE_CLASS}-placeholder`)
  handlePlaceholder.title = HANDLE_TITLE
  orderingTutorial.append(
    'you can drag tracks by their ',
    handlePlaceholder,
    ' to reorder them',
  )
  orderingTutorial.classList.add('aside')
  membershipForm.insertBefore(orderingTutorial, membershipContainer)

  const orderInputs = getOrderInputs()

  for (let i = 0; i < orderInputs.length; i++) {
    const orderInput = orderInputs[i]

    orderInput.addEventListener('change', ev => {
      // swap with the targetted number
      const orderInputAtTargetIndex = getOrderInputs()[Number.parseInt(orderInput.value, 10) - 1]

      if (orderInputAtTargetIndex !== undefined) {
        orderInputAtTargetIndex.value = orderInput.oldValue
      }

      sortable.sort(sortable.toArray().sort(
        (a, b) => {
          const getValueForId = id => parseInt(membershipContainer.querySelector(`[data-id="${id}"] input.order`).value, 10)
          return getValueForId(a) - getValueForId(b)
        },
      ), true)
      normalise()
    })

    normalise()
  }
}

const bindDeletionWarning = () => {
  const deleteButton = document.getElementById('delete-track-list')
  if (deleteButton === null) {
    return
  }

  deleteButton.addEventListener('click', e => {
    if (!confirm('are you sure? the list will be permanently deleted')) {
      e.preventDefault()
    }
  })
}

document.addEventListener('DOMContentLoaded', () => {
  bindIconOptions()
  bindMembershipForm()
  bindDeletionWarning()
})
