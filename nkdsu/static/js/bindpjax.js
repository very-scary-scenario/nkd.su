var $loading;
var messages = ['loading…', 'hang on…', 'please hold…', 'one moment…', 'be ready…', 'sit tight…', '*spinner*'];
var loadingTimeout;

function shuffleLoading() {
  $loading.text(messages[Math.floor(Math.random() * messages.length)]);
}

$(document).ready(function(){
  $(document).pjax('a[href]', '#everything');
  $.pjax.defaults.timeout = 5000;

  var $body = $('body');
  $loading = $('#loading');

  $(document).on('pjax:send', function() {
    shuffleLoading();
    loadingTimeout = setTimeout(function() {
      $body.addClass('loading');
    }, 500);
  });

  $(document).on('pjax:success', function() {
    $body.removeClass('loading');
    clearTimeout(loadingTimeout);
  });

  $(document).on('pjax:end', function() {
    bindSelection();
  });
});
