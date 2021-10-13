function bindAjaxableLinks(trackElement) {
  const BOUND_ATTR = 'data-ajax-bound'

  if (trackElement.hasAttribute(BOUND_ATTR)) { return }

  trackElement.querySelectorAll('.ajaxable').forEach(function(link) {
    link.addEventListener('click', function(e) {
      e.preventDefault()
      e.stopPropagation()

      const url = new URL(link.getAttribute('href'), document.baseURI)
      url.searchParams.append('ajax', 'yeah')

      trackElement.classList.add('pending')
      fetch(url).then(function(response) {
        return response.text()
      }).then(function(text) {
        trackElement.outerHTML = text
        bindAllAjaxableLinks()
      })
    })
  })

  trackElement.setAttribute(BOUND_ATTR, 'true')
}

function bindAllAjaxableLinks() {
  document.querySelectorAll('.track').forEach(bindAjaxableLinks)
}

document.addEventListener('DOMContentLoaded', bindAllAjaxableLinks)
