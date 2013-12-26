$(document).ready(function(){
  sel = 'form#search input#query'

  $(sel).focus(function() {
    if ($(this).hasClass('default') && $(this).val() == $(this).attr('default')) {
      $(this).removeClass('default');
      $(this).val('');
    }
  });

  $(sel).blur(function() {
    if ($(this).val() == '') {
      $(this).addClass('default');
      $(this).val($(this).attr('default'));
    }
  });
});
