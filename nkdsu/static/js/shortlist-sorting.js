/* global Sortable csrfPost */

function bindShortlistSorting() {
  const TOUCH_DELAY = 300
  const shortlistContainer = document.getElementById('shortlist')
  const shortlistOrderURL = document.getElementById('shortlist-order-url').innerText

  if (shortlistContainer === null) {
    return
  }

  function handleChange(e) {
    const data = new FormData()
    const items = sortable.toArray()

    for (let i = 0; i < items.length; i++) {
      data.append('shortlist[]', items[i])
    }

    csrfPost(shortlistOrderURL, {
      method: 'post',
      body: data,
      redirect: 'manual',
    }).then(text => {
      if (text === 'reload') {
        alert("You've added stuff to the shortlist since you last loaded the front page. Please reload before making any more changes.")
      }
    })
  }

  const sortable = Sortable.create(shortlistContainer, {
    delay: TOUCH_DELAY,
    delayOnTouchOnly: true,
    onSort: handleChange,
    dataIdAttr: 'data-shortlist-pk',
  })
}

document.addEventListener('DOMContentLoaded', bindShortlistSorting())
