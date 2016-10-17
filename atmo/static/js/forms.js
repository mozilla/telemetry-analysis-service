$(function() {
  // apply datetimepicker initialization
  $('.datetimepicker').datetimepicker({
    sideBySide: true, // show the time picker and date picker at the same time
    useCurrent: false, // don't automatically set the date when opening the dialog
    format: 'YYYY-MM-DD HH:mm',
    stepping: 5,
    toolbarPlacement: 'top',
    showTodayButton: true,
    showClear: true,
    showClose: true
  });

  $('form').on('submit', function(event){
    var $form = $(this);
    var $submit = $form.find('button[type=submit]');
    var $cancel = $form.find("a:contains('Cancel')");
    var $reset = $form.find('button[type=reset]');
    var submit_label = $submit.text();
    var wait_label = 'Please wait…';

    // disable submit button and change label
    $submit.addClass('disabled').find('.submit-button').text(wait_label);

    // hide cancel button
    $cancel.addClass('hidden');

    var reset_callback = function(event) {
      // re-enable submit button
      $submit.removeClass('disabled')
        .find('.submit-button')
        .text(submit_label);
      // show cancel button again
      $cancel.removeClass('hidden');
      // hide reset button
      $reset.addClass('hidden');
    };
    // show reset button to be able to reset form
    $reset.removeClass('hidden').click(reset_callback);
  });
});
