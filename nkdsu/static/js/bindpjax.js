var $loading;
var messages = ['loading…', 'hang on…', 'please hold…', 'one moment…', 'be ready…', 'sit tight…', 'matte~', '*spinner*'];
var loadingTimeout;
var lastMessage;

function shuffleLoading() {
  var choice = messages[Math.floor(Math.random() * messages.length)];

  if (choice === lastMessage) {
    shuffleLoading();
  } else {
    $loading.text(choice);
    lastMessage = choice;
  }
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
