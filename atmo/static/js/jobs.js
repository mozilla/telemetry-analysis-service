$(function() {
    var root = this;
    var $holder = $("#notebook-holder");
    var content = $("#notebook-content").val();

    if (content) {
        var parsed = JSON.parse(content);
        console.log("rendering");
        var notebook = root.notebook = nb.parse(parsed);
        $holder.empty()
        $holder.append(notebook.render());
        Prism.highlightAll();
    }
});
