document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('body.staff a.vote-link').forEach(voteLink => {
    voteLink.addEventListener('click', e => {
      e.preventDefault()
      document.body.classList.toggle('tracks-expanded')
      document.body.classList.toggle('tracks-collapsed')
    })
  })
})
