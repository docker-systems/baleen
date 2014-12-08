#!/usr/bin/env python
import os
import sys

# Uncomment to track down naive datetime objects
#import warnings
#warnings.simplefilter('error', RuntimeWarning)

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "baleen.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
