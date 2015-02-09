import inspect
import logging
import traceback
import re
import sys

from importlib import import_module

from baleen.action import Action


class NoSuchAction(Exception):

    def __init__(self, *args, **kwargs):
        self.details = kwargs.get('details', {})

    def __unicode__(self):
        return "No such action %s in group %s" % (
                self.details.get('action'),
                self.details.get('group')
                )


log = logging.getLogger('baleen.action')
_action_map = None


def get_label(action_cls):
    """
    Use the label attribute of a class or automatically convert a CamelCase
    class name to a underscore version.

    >>> class BlahBlahAction(object):
    ...     pass
    ...
    >>> get_label(BlahBlahAction)
    'blah_blah'
    >>> class BlahBlahSSHAction(object):
    ...     pass
    ...
    >>> get_label(BlahBlahSSHAction)
    'blah_blah_ssh'
    """
    label = getattr(action_cls, 'label', None)
    if label is None:
        label = action_cls.__name__
        action_i = label.rfind('Action')
        if action_i == len(label) - len('Action'):
            label = label[:-(len('Action'))]
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', label)
        label = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    return label


def _load_action_map(ACTION_MODULES):
    """
    Load various modules that are expected to have subclasses of Action

    There is a smell here I'd like to fix, where if you specify abstract=True
    on an Action class, the subclasses will also appear to be abstract.

    This might be resolvable using Python metaclass stuff, but that looks
    like a fair bit of work to understand.

    >>> _load_action_map({'test': 'baleen.action.project'})['test'].keys()
    ['sync_repo', 'git', 'clone_repo', 'create', 'import_build_definition', 'build']
    """
    action_map = {}
    for group, module in ACTION_MODULES.items():
        try:
            action_map[group] = _load_module(group, module)
        except Exception:
            action_map[group] = None
            log.error("Exception while trying to load action module %s as group %s" %
                    (module, group)
                    )
            print sys.exc_info()[0]
            print traceback.format_exc()
    return action_map


def _load_module(group, module):
    action_module = import_module(module)
    action_map = {}
    for name, obj in inspect.getmembers(action_module):
        if inspect.isclass(obj) and issubclass(obj, Action):
            if Action == obj or (
                    getattr(obj, 'abstract', False) and
                    not hasattr(obj, 'label')
                    ):
                pass
            else:
                l = get_label(obj)
                log.info("Found action %s:%s in module %s" % (group, l, module))
                action_map[l] = obj
        elif name == 'init_actions':
            log.info("Found init action for module %s" % (module,))
            obj()
    return action_map


def get_action_object(action_details):
    from django.conf import settings
    global _action_map
    if _action_map is None:
        _action_map = _load_action_map(settings.ACTION_MODULES)
    # copy so we don't destroy it
    ad = dict(action_details)

    group = ad.pop('group')
    action = ad.pop('action')
    opts = ad

    action_group = _action_map.get(group, {})
    action_cls = action_group.get(action)
    if action_cls is None:
        if action_group is None:
            log.info("Couldn't find action group or class for action %s:%s"
                    % (group, action)
                    )
        else:
            log.info("Couldn't find action class for action %s:%s, action group "
                    + "was present, so this could indicate a configuration issue."
                    % (group, action)
                    )
            log.info("Action group was present however, " % (group, action))
        raise NoSuchAction(details=ad)

    log.info("Found action class %s for action %s:%s, initialising with %s" % (
        action_cls, group, action, str(opts)
        ))
    return action_cls(**opts)
