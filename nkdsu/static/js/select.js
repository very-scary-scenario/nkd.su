function stick(time) {
  if (($('div#selhead').offset().top < ($(window).scrollTop() + $(window).height() - $('div#selhead').height())) == ($('div#stick div.stuck').css('display') != 'none')) {
    if ($('div#stick div.stuck').css('display') != 'none') {
      $('div#stick div.stuck').slideUp(time);
    } else {
      $('div#stick div.stuck').slideDown(time);
    }
  }
}

// selection representation 
function updateSelection(data) {
  const selectionElement = document.getElementById('selection')

  // update document
  selectionElement.innerHTML = data
  document.getElementById('stick').innerHTML = document.getElementById('selhead').innerHTML

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

  // make div#stick.invisible if necessary
  // ...but don't check too often, thanks stackoverflow question 8915376
  var scroll_ok = true;
  setInterval(function() { scroll_ok = true; }, 50);
  $(window).scroll(function() {
    if (scroll_ok === true) {
      scroll_ok = false;
      stick(200);
    }
  });

  // scroll to bottom when asked
  $('div#stick div.stuck h3').on("click", function() {
    window.scrollTo(0,$('div#selection').offset().top)
  })
}

function bindSelection() {
  // prevent clicking on a voter or an artist fold from selecting a track 
  $("li.vote a, summary").click(function(event) {
    event.stopPropagation()
  })

  $.post(getSelectionURL, function(data) {
    updateSelection(data)
  })

  // toggling selection
  $(".track.selectable").on("click", function(event) {
    if (!$(event.target).is('a')) {
      $(this).addClass('pending')
      var pk_map = { track_pk: [$(this).attr('data-pk')] }
      if (!$(this).hasClass("selected")) {
        $.post(selectURL, pk_map, function(data) {
          updateSelection(data)
        })
      } else {
        $.post(deselectURL, pk_map, function(data) {
          updateSelection(data)
        })
      }
    }
  })
}

document.addEventListener('DOMContentLoaded', bindSelection)
