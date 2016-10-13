$(function() {
  // apply datetimepicker initialization
  $('.datetimepicker').datetimepicker({
    sideBySide: true, // show the time picker and date picker at the same time
    useCurrent: false, // don't automatically set the date when opening the dialog
    widgetPositioning: {vertical: 'bottom'}, // make sure the picker shows up below the control
    format: 'YYYY-MM-DD h:mm',
  });
});
