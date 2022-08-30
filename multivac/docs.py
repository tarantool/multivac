#!/usr/bin/env python

import glob
import os

from sensors.failures import specific_failures, generic_failures

log_examples_path = 'docs/gather_job_data/'


def describe_failure_type(failure_spec: dict, heading_marker='-'):
    type_ = failure_spec['type']
    # anchor and heading
    yield f'\n..  _{type_}:\n\n{type_}\n{heading_marker * len(type_)}\n\n'

    if 'description' in failure_spec:
        yield f"{failure_spec['description']}\n\n"

    yield "Regular expressions:\n\n..  code-block:: python\n\n"
    for regexp in failure_spec['re']:
        yield f"    r'{regexp}'\n"

    files = glob.glob(
        os.path.join(
            log_examples_path,
            '_includes/'
            f'{type_}*.log')
    )

    if len(files) > 0:
        for file in files:
            included_file = os.path.split(file)
            yield '\nLog example:\n\n'
            yield f'..  literalinclude:: _includes/{included_file[1]}\n' \
                  f'    :language: console\n\n'


if __name__ == '__main__':

    failures_rst_path = 'docs/gather_job_data/failures.rst'
    with open(failures_rst_path, 'w') as failures_rst:
        print(f'Autogenerating {failures_rst_path}')
        failures_rst.writelines(
            '..  include:: _includes/failures.rst\n\n'
        )

        failure_specs_sorted = list(sorted(
            generic_failures + specific_failures, key=lambda x: x['type']
        ))
        for failure_spec in failure_specs_sorted:
            failures_rst.writelines(describe_failure_type(failure_spec))
