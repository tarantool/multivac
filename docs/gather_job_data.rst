gather_job_data.py
==================

Gathering data about workflow jobs.

Writing options
---------------

Gathered data can be written to a CSV or JSON file,
configured with `--format [csv|json]` option.
There is no default option and without `--format`
there will be no output file.

..  code-block:: console

    $ ./multivac/gather_job_data.py --format csv

The resulting output will look like this:

..  literalinclude:: ./gather_job_data/_includes/workflows.csv
    :language: text

Same with JSON:

..  code-block:: console

    $ ./multivac/gather_job_data.py --format json

..  literalinclude:: ./gather_job_data/_includes/workflows.json
    :language: json


Limiting and filtering workflows
--------------------------------

Workflows which were skipped or cancelled won't be processed.

To gather data from a number of most recent workflows, use `--latest`:

..  code-block:: console

    $ ./multivac/gather_job_data.py --latest 1000