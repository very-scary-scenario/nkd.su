$(document).pjax('a', '#everything');

$(document).on('pjax:complete', function() {
  bindSelection();
});
