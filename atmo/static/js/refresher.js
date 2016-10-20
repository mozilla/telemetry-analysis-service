$(function() {
  $(document).ready(function() {
      var refresh_url = $('body').attr('data-refresh-url'),
          content_container = '#content-container',
          refresh_container = '#refresh-container',
          refresh_timer = '#refresh-timer',
          refresher = $('#refresher'),
          timeout = 60,
          timeout_id;

      // if a refresher URL was found
      if (jQuery.type(refresh_url) !== "undefined") {
        var countdown = timeout;
        var updateTimeout = function() {
          if (countdown == 0) {
            $(content_container).load(
              refresh_url + ' ' + refresh_container,
              function(response, status, xhr) {
                if (status == 'error') {
                  $(refresher).addClass('hidden');
                  if (timeout_id) {
                    window.clearTimeout(timeout_id);
                  }
                }
              }
            );
            countdown = timeout;
          } else {
            countdown = countdown - 1;
            if (countdown == 0) {
              var countdown_label = 'ing now';
            } else {
              var countdown_label = ' in ' + countdown + 's';
            }
            $(refresh_timer).text(countdown_label);
          }
          timeout_id = window.setTimeout(updateTimeout, 1000);
        };
        // show the refresher
        $(refresher).removeClass('hidden');
        timeout_id = window.setTimeout(updateTimeout, 0);
      }
  });
});
