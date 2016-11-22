$(function() {
  AtmoCallbacks = $.Callbacks();
  var tooltip = function() {
    $('[data-toggle="tooltip"]').tooltip();
    $('[data-toggle="confirmation"]').confirmation({
      rootSelector: '[data-toggle="confirmation"]',
    });
  };
  AtmoCallbacks.add(tooltip);
  $(document).ready(function() {
    AtmoCallbacks.fire();
  });
});
