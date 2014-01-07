$(document).ready(function(){
  $(document).pjax('a', '#everything');
  $.pjax.defaults.timeout = 5000;

  $(document).on('pjax:complete', function() {
    bindSelection();
  });
});
