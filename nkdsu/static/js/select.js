// selection representation 
function updateSelection(text) {
  const selectionElement = document.getElementById('selection')

  // update document
  selectionElement.innerHTML = text

  // build a list of IDs of selected tracks
  let selectedTracks = []
  selectionElement.querySelectorAll('.minitrack').forEach(function(miniTrackElement) {
    selectedTracks.push(miniTrackElement.getAttribute('data-pk'))
  })
  
  // ensure selected tracks elsewhere in the page are marked as such and vice-versa
  document.querySelectorAll('.track[data-pk]').forEach(function(trackElement) {
    // if the selectedTracks doesn't match one of our selection statuses...
    if ((selectedTracks.indexOf(trackElement.getAttribute('data-pk')) != -1) != trackElement.classList.contains('selected')) {
      trackElement.classList.toggle('selected')
    }
    trackElement.classList.remove('pending')
  })

  // enable select all button
  const selectAllButtons = document.querySelectorAll('.select_all')
  selectAllButtons.forEach(function(selectAllButton) {
    selectAllButton.addEventListener('click', function(e) {
      e.preventDefault()
      const data = new FormData
      document.querySelectorAll('.track.selectable').forEach(function(selectableTrack) {
        data.append('track_pk[]', selectableTrack.getAttribute('data-pk'))
        selectableTrack.classList.add('pending')
      })

      csrfPost(selectAllButton.getAttribute('data-href'), { method: 'post', body: data }).then(function(text) {
        updateSelection(text)
      })
    })
  })

  // explicitly clear selection when user mass-votes
  document.querySelectorAll('a.mass_vote').forEach(function(massVoteElement) {
    massVoteElement.addEventListener('click', function(e) {
      csrfPost(clearSelectionURL, { method: 'post' }).then(function(text) {
        updateSelection(text)
      })
    })
  })

  // do js-friendly actions without reloading if possible
  document.querySelectorAll('.selection .minitrack').forEach(function(minitrack) {
    minitrack.querySelector("a[name='deselect']").addEventListener('click', function(e) {
      e.preventDefault()
      const data = new FormData()
      data.append('track_pk[]', minitrack.getAttribute('data-pk'))
      csrfPost(deselectURL, { method: 'post', body: data }).then(function(text) {
        updateSelection(text)
      })
    })
  })

  document.querySelectorAll("a[name='clear_selection']").forEach(function(clearSelectionElement) {
    clearSelectionElement.addEventListener('click', function(e) {
      e.preventDefault()
      csrfPost(clearSelectionURL, { method: 'post' }).then(function(text) {
        updateSelection(text)
      })
    })
  })
}

function bindSelection() {
  // prevent clicking on a voter or an artist fold from selecting a track 
  document.querySelectorAll('li.vote a, summary').forEach(function(element) {
    element.addEventListener('click', function(e) {
      e.stopPropagation()
    })
  })

  csrfPost(getSelectionURL, { method: 'post' }).then(function(text) {
    updateSelection(text)
  })

  // toggling selection
  document.querySelectorAll('.track.selectable').forEach(function(trackElement) {
    trackElement.addEventListener('click', function(e) {
      if (e.target.tagName !== 'A') {
        trackElement.classList.add('pending')
        const data = new FormData()
        data.append('track_pk[]', trackElement.getAttribute('data-pk'))
        const url = trackElement.classList.contains('selected') ? deselectURL : selectURL
        csrfPost(url, { method: 'post', body: data }).then(function(text) {
          updateSelection(text)
        })
      }
    })
  })
}

document.addEventListener('DOMContentLoaded', bindSelection)
