$(function() {
  $.fn.atmoNotebook = function() {
    var container = this,
        content_given = container.attr('data-content-given'),
        download_url = container.attr('data-download-url');
    var fail = function() {
      container.text('Apologies, could not load Notebook content.');
    };
    var render = function(data) {
      if (data) {
        var notebook = nb.parse(data);
        container.empty();
        container.append(notebook.render());
        Prism.highlightAll();
      };
    }
    if (content_given == 'true') {
      var content = container.children().filter('textarea').val();
      render(JSON.parse(content));
    } else if (jQuery.type(download_url) !== 'undefined') {
      $.get(download_url).done(render).fail(fail);
    }
  };
});

$(document).ready(function() {
  $('#notebook-content').atmoNotebook();
});
