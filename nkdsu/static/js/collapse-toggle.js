document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('body.staff a.vote-link').forEach(function(voteLink) {
    voteLink.addEventListener('click', function(e) {
      e.preventDefault()
      document.body.classList.toggle('tracks-expanded')
      document.body.classList.toggle('tracks-collapsed')
    })
  })
})
