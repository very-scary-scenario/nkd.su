$(document).ready(function(){
  $(document).pjax('a', '#everything');
  $.pjax.defaults.timeout = 5000;

  var $body = $('body');

  $(document).on('pjax:send', function() {
    $body.addClass('loading');
  });

  $(document).on('pjax:complete', function() {
    $body.removeClass('loading');
  });

  $(document).on('pjax:end', function() {
    bindSelection();
  });
});
