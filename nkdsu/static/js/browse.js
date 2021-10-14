function bindCategorySearch() {
  const DEBOUNCE_DELAY = 300
  let debounce = null

  const filterForm = document.getElementById('category-search-form')
  const sections = document.querySelectorAll('.browsable-groups section')

  filterForm.addEventListener('submit', e => {
    e.preventDefault() // we're gonna do filtering locally
  })

  if (filterForm === null) {
    return
  }
  const filterInput = filterForm.querySelector('input')
  let currentQuery = filterInput.value

  function updatePage() {
    const re = new RegExp(currentQuery, 'i')
    sections.forEach(section => {
      section.setAttribute('data-contains-matches', '')

      section.querySelectorAll('ul > li').forEach(item => {
        const matched = item.innerText.search(re) !== -1
        if (matched !== (item.classList.contains('matched'))) {
          item.classList.toggle('matched')
        }
        if (matched) {
          section.setAttribute('data-contains-matches', 'true')
        }
      })
    })

    const newUrl = new URL(document.location)
    newUrl.searchParams.set(filterInput.getAttribute('name'), currentQuery)
    history.replaceState(currentQuery, currentQuery, newUrl)
  }

  function respondToInput(e) {
    const newQuery = filterInput.value
    if (currentQuery !== newQuery) {
      currentQuery = newQuery
      if (debounce !== null) { clearTimeout(debounce) }
      debounce = setTimeout(updatePage, DEBOUNCE_DELAY)
    }
  }

  filterInput.addEventListener('change', respondToInput)
  filterInput.addEventListener('input', respondToInput)
}

document.addEventListener('DOMContentLoaded', bindCategorySearch)
