import inspect
import re

from django.conf import settings
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

_action_map = None

def get_label(action_cls):
    """
    >>> class BlahBlahAction(object):
    ...     pass
    ...
    >>> get_label(BlahBlahAction)
    'blah_blah'
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

def _load_action_map():
    action_map = {}
    for group, module in settings.ACTION_MODULES.items():
        action_module = import_module(module)
        for name, obj in inspect.getmembers(action_module):
            if inspect.isclass(obj) and issubclass(obj, Action):
                if Action == obj or (
                        getattr(obj, 'abstract', False) and
                        not hasattr(obj, 'label')
                        ):
                    pass
                else:
                    l = get_label(obj)
                    print("Found action %s:%s in module %s" % (group, l, module))
                    action_map.setdefault(group, {})
                    action_map[group][l] = obj
    return action_map


def get_action_object(action_details):
    global _action_map
    if _action_map is None:
        _action_map = _load_action_map()
    # copy so we don't destroy it
    ad = dict(action_details)

    group = ad.pop('group')
    action = ad.pop('action')
    opts = ad

    action_cls = _action_map.get(group, {}).get(action)
    if action_cls is None:
        raise NoSuchAction(details=ad)

    return action_cls(opts)
