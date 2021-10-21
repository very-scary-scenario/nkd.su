/* global csrfPost clearSelectionURL deselectURL getSelectionURL selectURL */

// selection representation
function updateSelection(text) {
  const selectionElement = document.getElementById('selection')
  let wasOpenBeforeUpdate = false
  const originalDetailsElement = document.getElementById('selection-details')
  if (originalDetailsElement !== null) {
    wasOpenBeforeUpdate = !!(originalDetailsElement.hasAttribute('open'))
  }

  // update document
  selectionElement.innerHTML = text

  if (wasOpenBeforeUpdate) {
    document.getElementById('selection-details').setAttribute('open', 'true')
  }

  // build a list of IDs of selected tracks
  const selectedTracks = []
  selectionElement.querySelectorAll('.minitrack').forEach(miniTrackElement => {
    selectedTracks.push(miniTrackElement.getAttribute('data-pk'))
  })

  // ensure selected tracks elsewhere in the page are marked as such and vice-versa
  document.querySelectorAll('.track[data-pk]').forEach(trackElement => {
    // if the selectedTracks doesn't match one of our selection statuses...
    if ((selectedTracks.indexOf(trackElement.getAttribute('data-pk')) !== -1) !== trackElement.classList.contains('selected')) {
      trackElement.classList.toggle('selected')
    }
    trackElement.classList.remove('pending')
  })

  // enable select all button
  const selectAllButtons = document.querySelectorAll('.select_all')
  selectAllButtons.forEach(selectAllButton => {
    selectAllButton.addEventListener('click', e => {
      e.preventDefault()
      const data = new FormData()
      document.querySelectorAll('.track.selectable').forEach(selectableTrack => {
        data.append('track_pk[]', selectableTrack.getAttribute('data-pk'))
        selectableTrack.classList.add('pending')
      })

      csrfPost(selectAllButton.getAttribute('data-href'), { method: 'post', body: data }).then(text => {
        updateSelection(text)
      })
    })
  })

  // explicitly clear selection when user mass-votes
  document.querySelectorAll('a.mass_vote').forEach(massVoteElement => {
    massVoteElement.addEventListener('click', e => {
      csrfPost(clearSelectionURL, { method: 'post' }).then(text => {
        updateSelection(text)
      })
    })
  })

  // do js-friendly actions without reloading if possible
  document.querySelectorAll('.selection .minitrack').forEach(minitrack => {
    minitrack.querySelector("a[name='deselect']").addEventListener('click', e => {
      e.preventDefault()
      const data = new FormData()
      data.append('track_pk[]', minitrack.getAttribute('data-pk'))
      csrfPost(deselectURL, { method: 'post', body: data }).then(text => {
        updateSelection(text)
      })
    })
  })

  document.querySelectorAll("a[name='clear_selection']").forEach(clearSelectionElement => {
    clearSelectionElement.addEventListener('click', e => {
      e.preventDefault()
      csrfPost(clearSelectionURL, { method: 'post' }).then(text => {
        updateSelection(text)
      })
    })
  })
}

function bindSelection() {
  // prevent clicking on a voter or an artist fold from selecting a track
  document.querySelectorAll('li.vote a, summary').forEach(element => {
    element.addEventListener('click', e => {
      e.stopPropagation()
    })
  })

  csrfPost(getSelectionURL, { method: 'post' }).then(text => {
    updateSelection(text)
  })

  // toggling selection
  document.querySelectorAll('.track.selectable').forEach(trackElement => {
    trackElement.addEventListener('click', e => {
      if (e.target.tagName !== 'A') {
        trackElement.classList.add('pending')
        const data = new FormData()
        data.append('track_pk[]', trackElement.getAttribute('data-pk'))
        const url = trackElement.classList.contains('selected') ? deselectURL : selectURL
        csrfPost(url, { method: 'post', body: data }).then(text => {
          updateSelection(text)
        })
      }
    })
  })
}

document.addEventListener('DOMContentLoaded', bindSelection)
