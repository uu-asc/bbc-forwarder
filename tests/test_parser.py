import unittest
import pandas as pd
from bbc_forwarder import parser


class Test_RemoveWhitespace(unittest.TestCase):
    def test(self):
        text = "Hebban  olla   uogala    nestas"
        expected = "Hebban olla uogala nestas"
        result = parser.remove_whitespace(text)
        self.assertEqual(result, expected)


class Test_FindAmounts(unittest.TestCase):
    def test(self):
        text = """
        1200
        €120
        €1200
        €1200,00
        € 1200,00
        € 1,200.00
        € 1.200,00
        € 1 200,00
        € 1x200,00
        """
        expected = [
            '€120',
            '€1200',
            '€1200,00',
            '€ 1200,00',
            '€ 1,200.00',
            '€ 1.200,00',
            '€ 1 200,00',
        ]
        result = parser.find_amounts(text)
        self.assertListEqual(result, expected)


class Test_FindInstitute(unittest.TestCase):
    pass


class Test_ReplaceMonths(unittest.TestCase):
    def test(self):
        text = """
        1 januari 1999
        31-dec-2020
        """
        expected = """
        1 01 1999
        31-12-2020
        """
        result = parser.replace_months(text)
        self.assertEqual(result, expected)


class Test_FindDatestrings(unittest.TestCase):
    def test(self):
        text = """
        Hebban 1 1 1999
        olla 01 01 1999
        uogala 01 01 19999
        nestas 01 01 99
        hagunnan 1-1-1999
        hinase 1/1/1999
        hic 01.01.1999 anda
        thu 1.111.1999
        """
        expected = [
            '1 1 1999',
            '01 01 1999',
            '1-1-1999',
            '1/1/1999',
            '01.01.1999',
        ]
        result = parser.find_datestrings(text)
        self.assertListEqual(result, expected)


class Test_GetEarliest(unittest.TestCase):
    def test(self):
        datestrings = ['01-01-1999', '01-01-2020']
        expected = pd.Timestamp(day=1, month=1, year=1999)
        result = parser.get_earliest(datestrings)
        self.assertEqual(result, expected)


class Test_SearchName(unittest.TestCase):
    pass
