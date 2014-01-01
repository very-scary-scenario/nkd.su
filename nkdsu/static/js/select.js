$(document).ready(function(){
  // django shenanigans
  function csrfSafeMethod(method) {
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
  }

  var csrftoken = $.cookie('csrftoken');

  $.ajaxSetup({
    crossDomain: false,
    beforeSend: function(xhr, settings) {
      if (!csrfSafeMethod(settings.type)) {
          xhr.setRequestHeader("X-CSRFToken", csrftoken);
      }
    }
  });

  // prevent clicking on a voter from selecting a track 
  $("a.voter").click(function(event) {
    event.stopPropagation();
  });

  // stick to bottom of screen
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
    $('p.id').each(function() {
      selected_tracks.push($(this).text());
    });
    
    // ensure selected tracks are marked as such and vice-versa
    $("div.track").each(function() {
      // if the selected_tracks doesn't match one of our selection statuses...
      if (($.inArray(this.id, selected_tracks) != -1) != $(this).hasClass('selected')) {
        $(this).toggleClass('selected');
      }
      $(this).removeClass('pending');
    });

    // enable select all button
    $("a.select_all").click(function(event) {
      event.preventDefault();
      var all_selectable = [];
      $('div.track.selectable').each(function() {
        all_selectable.push(this.id);
        $(this).addClass('pending');
      });
      var id_map = { track_id: all_selectable };
      $.post($(this).attr('href'), id_map, function(data) {
        update_selection(data);
      });
    });

    // explicitly clear selection when user mass-votes
    $('a.mass_vote').click(function(event) {
      $.post('/do/clear_selection/', function(data) {
        update_selection(data);
      });
    });

    // do js-friendly actions without reloading if possible
    $("a.track_jspost").click(function(event) {
      event.preventDefault();
      var id_map = { track_id: $(this).closest('div.minitrack').find('p.id').text() };
      $.post($(this).attr('href'), id_map, function(data) {
        update_selection(data);
      });
    });

    $("a.selection_jspost").click(function(event) {
      event.preventDefault();
      $.post($(this).attr('href'), function(data) {
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

  $.post('/do/selection/', function(data) {
    update_selection(data);
  });

  // toggling selection
  $("div.track.selectable").on("click", function(event) {
    if (!$(event.target).is('a')) {
      $(this).addClass('pending');
      var id_map = { track_id: this.id };
      if (!$(this).hasClass("selected")) {
        $.post('/do/select/', id_map, function(data) {
          update_selection(data);
        });
      }
      else {
        $.post('/do/deselect/', id_map, function(data) {
          update_selection(data);
        });
      }
    }
  });
});
