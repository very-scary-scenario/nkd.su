function bindShortlistSorting() {
  const shortlistContainer = document.getElementById('shortlist')
  const shortlistOrderURL = document.getElementById('shortlist-order-url').innerText

  if (shortlistContainer === null) {
    return
  }

  function handleChange(e) {
    const data = new FormData()
    const items = sortable.toArray()
    const request = new Request(shortlistOrderURL, {
      headers: {'X-CSRFToken': csrftoken},
    })

    for (let i = 0; i < items.length; i++) {
      data.append('shortlist[]', items[i])
    }

    fetch(request, {
      method: 'post',
      body: data,
      redirect: 'manual',
    }).then(function(response) {
      return response.text()
    }).then(function(text) {
      console.log(text)
      if (text === 'reload') {
        alert("You've added stuff to the shortlist since you last loaded the front page. Please reload before making any more changes.")
      }
    })
  }

  const sortable = Sortable.create(shortlistContainer, {
    onSort: handleChange,
    dataIdAttr: 'data-shortlist-pk',
  })
}

document.addEventListener('DOMContentLoaded', bindShortlistSorting())
