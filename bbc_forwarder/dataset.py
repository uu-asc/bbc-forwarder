from typing import Literal, Callable
import pandas as pd
import bbc_forwarder.parser as parser
from bbc_forwarder.config import CONFIG


MsgStatus = Literal[
    'no_pdfs',
    'pdf_not_parsed',
    'too_many_pdfs',
    'no_student_matched',
    'more_than_one_matched_student',
    'more_than_one_sinh_id',
    'one_matched_sinh_id',
]


def format_dates(df: pd.DataFrame, date_format='%d-%m-%Y') -> pd.DataFrame:
    dtypes = ['datetime64[ns]', 'datetime64[ns, UTC]']
    for column in df.select_dtypes(include=dtypes):
        df[column] = df[column].dt.strftime(date_format)
    return df


def format_strings(df: pd.DataFrame, na_rep='') -> pd.DataFrame:
    dtypes = ['string']
    for column in df.select_dtypes(include=dtypes):
        df[column] = df[column].fillna(na_rep)
    return df


def get_status(grp) -> MsgStatus:
    pdfs = grp.loc[grp.is_pdf == True]
    n_pdfs = pdfs.attachment_id.nunique()

    if n_pdfs == 0:
        return 'no_pdfs'
    if n_pdfs > 1:
        return 'too_many_pdfs'
    if n_pdfs == 1:
        if not pdfs.is_parsed.any():
            return 'pdf_not_parsed'
        if not pdfs.found_student.any():
            return 'no_student_matched'

        n_studentnummers = pdfs.studentnummer.nunique()
        if n_studentnummers > 1:
            return 'more_than_one_matched_student'

        n_sinhids = pdfs.sinh_id.nunique()
        if n_sinhids > 1:
            return 'more_than_one_sinh_id'
        return 'one_matched_sinh_id'


def get_soort(grp) -> Literal['issue', 'csa', 'faculteit']:
    status = grp.status.iloc[0]
    if status != 'one_matched_sinh_id':
        return 'issue'

    if (grp.soort_inschrijving == 'S').any():
        return 'csa'
    return 'faculteit'


def get_address(keys) -> str|None:
    """Loop through `keys` and return the first address where the key matches a
    key in `CONFIG['forwarder']['address']`. Return None if no match was found."""
    address = CONFIG['forwarder']['address']
    for key in keys:
        if key.lower() in address:
            return address.get(key.lower())
    return None


def get_ontvanger(grp) -> str|None:
    soort = grp.soort.iloc[0]
    if soort in ['csa', 'issue']:
        return CONFIG['forwarder']['address']['csa']

    fields = ['opleiding', 'aggregaat_2', 'aggregaat_1', 'faculteit']

    search_terms = grp.query("opleiding.notna()").iloc[0].loc[fields].dropna().to_list()
    address = get_address(search_terms)
    return address


def apply_merge(df: pd.DataFrame, f: Callable, name: str) -> pd.DataFrame:
    new_field = (
        df
        .groupby('object_id')
        .apply(f, include_groups=False)
        .rename(name)
    )
    merged = df.merge(
        new_field,
        left_on = 'object_id',
        right_index = True,
    )
    return merged


def create_dataset(messages) -> pd.DataFrame:
    results = (
        messages
        .pipe(format_dates)
        .convert_dtypes()
        # .pipe(format_strings)
        .pipe(apply_merge, f=get_status, name='status')
        .pipe(apply_merge, f=get_soort, name='soort')
        .pipe(apply_merge, f=get_ontvanger, name='ontvanger')
    )
    return results
