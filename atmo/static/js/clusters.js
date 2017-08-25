$(function() {
  var instructionFlipper = function() {
    if ($(this).hasClass("active")) {
      $(".with-nfs").hide();
      $(".without-nfs").show();
      $(this).removeClass("active");
    } else {
      $(".with-nfs").removeClass("hidden");
      $(".with-nfs").show();
      $(".without-nfs").hide();
      $(this).addClass("active");
    }
  };
  AtmoCallbacks.add(function() {
    $('#instruction-flipper').on('click', instructionFlipper);
  });
});
