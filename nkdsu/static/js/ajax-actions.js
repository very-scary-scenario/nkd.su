function handleAjaxClick(e) {
  e.stopPropagation();
  e.preventDefault();

  var trackElement = $($(e.currentTarget).parents('.track'));
  trackElement.addClass('pending');

  $.get(e.currentTarget.getAttribute('href'), {ajax: 'yeah'}, function(data) {
    trackElement.after(data);
    trackElement.remove();
    rebind();
  });
}


function rebind() {
  $('.ajaxable').off('click', handleAjaxClick);
  $('.ajaxable').on('click', handleAjaxClick);
}

rebind();
