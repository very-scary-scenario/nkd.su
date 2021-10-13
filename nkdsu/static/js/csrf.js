function getCookie(name) {
  let cookieValue = null
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';')
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim()
      // Does this cookie string begin with the name we want?
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1))
        break
      }
    }
  }
  return cookieValue
}

const csrftoken = getCookie('csrftoken')

/* eslint-disable no-unused-vars */
function csrfPost(url, params) {
  /* eslint-enable no-unused-vars */
  const request = new Request(url, {
    headers: { 'X-CSRFToken': csrftoken },
  })
  return fetch(request, params).then(function(response) {
    return response.text()
  })
}
