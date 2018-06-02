function bindCollapseToggle() {
  $('body.staff a.vote-link').click(function(e) {
    e.preventDefault();
    $('body').toggleClass('tracks-expanded').toggleClass('tracks-collapsed');
  });
}

$(document).ready(function(){
  bindCollapseToggle();
});
