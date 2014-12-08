#!/bin/sh
mkdir -p /var/local/baleen/htmlcov_projects
watchmedo shell-command --pattern '*.tar.gz' --command 'echo ${watch_src_path} && gzip -t "${watch_src_path}" && tar xvfz "${watch_src_path}" -C /var/www/django/baleen/htmlcov_projects' /var/local/baleen/htmlcov_projects/
