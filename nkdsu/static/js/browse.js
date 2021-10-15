function bindCategorySearch() {
  const DEBOUNCE_DELAY = 300
  let debounce = null

  const filterForm = document.getElementById('category-search-form')
  const sections = document.querySelectorAll('.browsable-groups section')

  filterForm.addEventListener('submit', e => {
    e.preventDefault() // we're gonna do filtering locally
    updatePage(true)
  })

  if (filterForm === null) {
    return
  }
  const filterInput = filterForm.querySelector('input')

  // the query we're currently actually filtering with
  let currentQuery = filterInput.value

  // the query that was present at "page load" (or history state push)
  let submittedQuery = currentQuery

  function highlightMatches(item, re, hideAll) {
    const textElement = item.querySelector('a') || item
    let text = item.getAttribute('data-name')
    if (!hideAll) {
      text = text.replaceAll(re, match => { return `[[[[${match}]]]]` })
    }
    textElement.innerText = text
    if (!hideAll) {
      textElement.innerHTML = textElement.innerHTML.replaceAll('[[[[', '<span class="fragment">').replaceAll(']]]]', '</span>')
    }
  }

  function updatePage(pushNewHistoryState) {
    const re = new RegExp(currentQuery || '.*', 'ig')
    sections.forEach(section => {
      section.setAttribute('data-contains-matches', '')

      section.querySelectorAll('ul > li').forEach(item => {
        const matched = item.getAttribute('data-name').search(re) !== -1
        highlightMatches(item, re, !currentQuery)
        if (matched !== (item.classList.contains('matched'))) {
          item.classList.toggle('matched')
        }
        if (matched) {
          section.setAttribute('data-contains-matches', 'true')
        }
      })
    })

    const newUrl = new URL(document.location)

    if (currentQuery) {
      newUrl.searchParams.set(filterInput.getAttribute('name'), currentQuery)
    } else {
      newUrl.searchParams.delete(filterInput.getAttribute('name'))
    }

    if (pushNewHistoryState) {
      // the user has explicitly hit enter, so we should try to behave like
      // their browser would if this was a normal GET form; we'll replace the
      // current history state with how it was when it was last pushed to, and
      // then push a new state with the newly-submitted value. that way, they
      // can hit back and get to the last query they loaded or submitted:
      history.replaceState({ query: submittedQuery }, submittedQuery, newUrl)
      history.pushState({ query: currentQuery }, currentQuery, newUrl)
      submittedQuery = currentQuery
    } else {
      history.replaceState({ query: currentQuery }, currentQuery, newUrl)
    }
  }

  function respondToInput(immediateNewState) {
    const newQuery = filterInput.value
    if (currentQuery !== newQuery) { currentQuery = newQuery }
    if (debounce !== null) { clearTimeout(debounce) }
    if (immediateNewState) { updatePage(true) } else {
      debounce = setTimeout(() => { updatePage(false) }, DEBOUNCE_DELAY)
    }
  }

  filterInput.addEventListener('change', e => { respondToInput(true) })
  filterInput.addEventListener('input', e => { respondToInput(false) })

  window.onpopstate = e => {
    if (e.state !== null && e.state.query !== undefined) {
      currentQuery = submittedQuery = e.state
      filterInput.value = currentQuery
      updatePage(false)
    }
  }

  updatePage()
}

document.addEventListener('DOMContentLoaded', bindCategorySearch)
