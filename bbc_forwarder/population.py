"""population module
=================

The population module loads and prepares the population data.

NOTE: Ensure OSIRIS-query is in the path (use: `sys.path.insert`)

More information
----------------
[https://github.com/uu-csa/osiris_query](OSIRIS-query)
"""

import flatbread

from query.results import QueryResult


population = QueryResult.read_pickle(
    "bbc/inschrijfhistorie_2020"
).frame.replace(
    {'faculteit': {'IVLOS': 'GST', 'RA': 'UCR', 'UC': 'UCU'}}
).pipe(
    flatbread.load.merge,
    QueryResult.read_pickle(
        "referentie/ref_OST_OPLEIDING"
    ).frame.pipe(
        flatbread.cols.normalize,
    ).pipe(
        flatbread.cols.select,
        ['opleiding', 'aggregaat_1', 'aggregaat_2']
    )
)
