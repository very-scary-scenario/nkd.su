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
function update_selection(data) {
  // update document
  $("div#selection").html(data);
  $("div#stick").html($("div#selhead").html());
  stick(0);

  // build a list of IDs of selected tracks
  var selected_tracks = [];
  $('.selection .minitrack').each(function() {
    selected_tracks.push($(this).attr('data-pk'));
  });
  
  // ensure selected tracks are marked as such and vice-versa
  $("li.track").each(function() {
    // if the selected_tracks doesn't match one of our selection statuses...
    if (($.inArray($(this).attr('data-pk'), selected_tracks) != -1) != $(this).hasClass('selected')) {
      $(this).toggleClass('selected');
    }
    $(this).removeClass('pending');
  });

  // enable select all button
  $("a.select_all").click(function(event) {
    event.preventDefault();
    var all_selectable = [];
    $('.track.selectable').each(function() {
      all_selectable.push($(this).attr('data-pk'));
      $(this).addClass('pending');
    });
    var pk_map = { track_pk: all_selectable };
    $.post($(this).attr('data-href'), pk_map, function(data) {
      update_selection(data);
    });
  });

  // explicitly clear selection when user mass-votes
  $('a.mass_vote').click(function(event) {
    $.post(clearSelectionURL, function(data) {
      update_selection(data);
    });
  });

  // do js-friendly actions without reloading if possible
  $("a[data-href='" + deselectURL + "']").click(function(event) {
    event.preventDefault();
    var pk_map = { track_pk: $(this).closest('div.minitrack').text() };
    $.post($(this).attr('data-href'), id_map, function(data) {
      update_selection(data);
    });
  });

  $("a[data-href='" + clearSelectionURL + "']").click(function(event) {
    event.preventDefault();
    $.post($(this).attr('data-href'), function(data) {
      update_selection(data);
    });
  });

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
    window.scrollTo(0,$('div#selection').offset().top);
  });
}

function bindSelection() {
  // prevent clicking on a voter or an artist fold from selecting a track 
  $("li.vote a, summary").click(function(event) {
    event.stopPropagation();
  });

  $.post(getSelectionURL, function(data) {
    update_selection(data);
  });

  // toggling selection
  $(".track.selectable").on("click", function(event) {
    if (!$(event.target).is('a')) {
      $(this).addClass('pending');
      var pk_map = { track_pk: [$(this).attr('data-pk')] };
      if (!$(this).hasClass("selected")) {
        $.post(selectURL, pk_map, function(data) {
          update_selection(data);
        });
      } else {
        $.post(deselectURL, pk_map, function(data) {
          update_selection(data);
        });
      }
    }
  });
}

$(document).ready(function(){
  bindSelection();
});
