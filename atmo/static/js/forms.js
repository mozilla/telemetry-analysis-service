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
});
