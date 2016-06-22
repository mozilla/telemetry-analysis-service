$(function() {
  // set up form element popovers
  $('[data-toggle="popover"]').popover();

  // apply validation for form controls
  $('input, select, textarea').not('[type=submit]').jqBootstrapValidation();

  // apply datetimepicker initialization
  $('.datetimepicker').datetimepicker({
    sideBySide: true, // show the time picker and date picker at the same time
    useCurrent: false, // don't automatically set the date when opening the dialog
    widgetPositioning: {vertical: 'bottom'}, // make sure the picker shows up below the control
    format: 'YYYY-MM-DD h:mm',
  });

  $(".editable-table").each(function(i, e) { // select the first row of each editable table
    $(e).find("tr:has(td)").first().addClass("selected");
    updateSelectedIdClasses($(e));
  });
  $(".editable-table tr:has(td)").click(function() {
    // allow selecting individual rows
    var parentTable = $(this).parents("table").first(); // the table containing the clicked row
    parentTable.find("tr").removeClass("selected");
    $(this).addClass("selected"); // select the clicked row
    updateSelectedIdClasses(parentTable);
  });
});

// given a jQuery table object, update selected object IDs based on which table it is
// for example, an input with the `selected-cluster` class should always contain the ID
// of the selected row in the cluster table
function updateSelectedIdClasses(editableTable) {
  // the first two columns of the tables should be row IDs, and row names
  var selectedId = editableTable.find("tr.selected td:first").text();
  var selectedName = editableTable.find("tr.selected td:nth-child(2)").text();

  // update objects as necessary
  switch (editableTable.attr("id")) {
    case "cluster-table":
      $(".selected-cluster").val(selectedId);
      $(".selected-cluster-name").text(selectedName);
      break;
    case "scheduled-spark-table":
      $(".selected-scheduled-spark").val(selectedId);
      $(".selected-scheduled-spark-name").text(selectedName);
      break;
  }
}