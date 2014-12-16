from baleen.action import Action

class FigAction(Action):

    def __init__(self, project, name, index, *arg, **kwarg):
        super(FigAction, self).__init__(project, name, index)
        self.fig_file = kwarg.get('fig_file')

    def __unicode__(self):
        return "FigAction: %s" % self.name

    def execute(self, stdoutlog, stderrlog, action_result):
        pass


class ProjectAction(Action):
    ACTIONS = ('create', 'sync', 'build')

    pass
