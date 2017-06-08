from celery.contrib.sphinx import TaskDocumenter, TaskDirective


class AtmoTaskDocumenter(TaskDocumenter):
    """
    A TaskDocument subclass to fix
    https://github.com/celery/celery/issues/4072 temporarily.
    """

    def check_module(self):
        """Normally checks if *self.object* is really defined in the module
        given by *self.modname*. But since functions decorated with the @task
        decorator are instances living in the celery.local module we're
        checking for that and simply agree to document those then.
        """
        modname = self.get_attr(self.object, '__module__', None)
        if modname and modname == 'celery.local':
            return True
        return super(TaskDocumenter, self).check_module()


def setup(app):
    """Setup Sphinx extension."""
    app.add_autodocumenter(AtmoTaskDocumenter)
    app.add_directive_to_domain('py', 'task', TaskDirective)
    app.add_config_value('celery_task_prefix', '(task)', True)
