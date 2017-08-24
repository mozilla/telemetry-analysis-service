$(function() {
  $.fn.atmoNotebook = function() {
    var container = this,
        content_given = container.attr('data-content-given'),
        download_url = container.attr('data-download-url'),
        zeppelin_url = container.attr('data-zeppelin-url');

    var fail = function() {
      container.html('<h4>Apologies, we could not load Notebook content.</h4>');
    };
    var current_script_path = function() {
      var scripts = $('script[src]');
      var current_script = scripts[scripts.length - 1].src;
      var current_script_chunks = current_script.split('/');
      var current_script_file = current_script_chunks[current_script_chunks.length - 1];
      return current_script.replace(current_script_file, '');
    };
    var render = function(data) {
      if (data) {
        container.empty();
        if (!data['nbformat']) {
          $.ajax({
             url: zeppelin_url,
             type:'GET',
             success: function(data){
                var md = new Remarkable();
                container.html(md.render($(data).find('#markdown').html()));
             }
          });
          container.html('<h4>Please download the Zeppelin notebook to view its contents.</h4>')
        } else {
          var notebook = nb.parse(data);
          container.append(notebook.render());
          Prism.plugins.autoloader.languages_path = current_script_path() + '../npm/prismjs/components/';
          Prism.highlightAll();
        }
      };
    }
    if (content_given == 'true') {
      var content = container.children().filter('textarea').val();
      render(JSON.parse(content));
    } else if (jQuery.type(download_url) !== 'undefined') {
      $.get(download_url).done(render).fail(fail);
    }
  };
  
  $.fn.atmoRenderZeppelin = function() {
    var md = new Remarkable();
    var renderedHTML = md.render(this.text());
    $('#renderedHTML').append(renderedHTML);
  };

  AtmoCallbacks.add(function() {
    $('#notebook-content').atmoNotebook();
    $('#markdown').atmoRenderZeppelin();
  });
});
