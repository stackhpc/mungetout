import unittest
from mungetout.convert import _clean_boot_volume  # noqa


class FilterTests(unittest.TestCase):
    def test_clean_boot_volume(self):
        item = (u'hpa',
                u'slot_0',
                u'secondary_boot_volume',
                u'logicaldrive 1 (600508B1001C6D568C431707B847FA3A)')
        expected = (u'hpa',
                    u'slot_0',
                    u'secondary_boot_volume',
                    u'logicaldrive 1')
        result = _clean_boot_volume(item)
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()
