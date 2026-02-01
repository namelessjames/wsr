import unittest
from wsr.i18n import I18n, init_i18n, _

class TestI18n(unittest.TestCase):
    def test_default_en(self):
        # Force english
        i18n = I18n(lang='en')
        self.assertEqual(i18n.translate('initializing'), 'Initializing WSR...')
        
    def test_de(self):
        i18n = I18n(lang='de')
        self.assertEqual(i18n.translate('initializing'), 'Initialisiere WSR...')

    def test_fallback(self):
        # Non-existent language should fallback to 'en'
        i18n = I18n(lang='fr')
        self.assertEqual(i18n.lang, 'en')
        self.assertEqual(i18n.translate('initializing'), 'Initializing WSR...')

    def test_formatting(self):
        i18n = I18n(lang='en')
        text = i18n.translate('starting_in', n=5)
        self.assertEqual(text, 'Starting in 5 seconds...')

    def test_global_helper(self):
        init_i18n('de')
        self.assertEqual(_('initializing'), 'Initialisiere WSR...')

if __name__ == '__main__':
    unittest.main()