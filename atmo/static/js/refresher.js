$(function() {
  $(document).ready(function() {
      var refresh_url = $('body').attr('data-refresh-url'),
          content_container = '#content-container',
          refresh_container = '#refresh-container',
          refresh_timer = '#refresh-timer',
          refresher = $('#refresher'),
          time = $('#time'),
          timeout = 60,
          timeout_id;
      var utc_now = function() {
        return moment().utcOffset(0).format('YYYY-MM-DD HH:mm:ss');
      }
      var updateTime = function() {
        time.attr('data-original-title', 'Current: ' + utc_now());
        window.setTimeout(updateTime, 1000);
      }
      updateTime();

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
