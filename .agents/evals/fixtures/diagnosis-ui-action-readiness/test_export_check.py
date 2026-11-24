import unittest

from export_check import check_export


class ReportPanel:
    def __init__(self, export_after):
        self.buttons = {'Open summary'}
        self.export_after = export_after
        self.exports = 0
        self.remaining_frames = None

    def click(self, label):
        if label not in self.buttons:
            raise LookupError(label)
        if label == 'Open summary':
            self.remaining_frames = self.export_after
            self._render()
        if label == 'Export CSV':
            self.exports += 1

    def wait_for_text(self, label):
        if label != 'Monthly summary':
            raise LookupError(label)

    def wait_for_button(self, label):
        while label not in self.buttons and self.remaining_frames not in (None, 0):
            self.remaining_frames -= 1
            self._render()
        if label not in self.buttons:
            raise LookupError(label)

    def _render(self):
        if self.remaining_frames == 0:
            self.buttons.add('Export CSV')


class ExportCheckTest(unittest.TestCase):
    def test_immediate_panel_exports_once(self):
        panel = ReportPanel(export_after=0)
        check_export(panel)
        self.assertEqual(panel.exports, 1)

    def test_delayed_panel_exports_once(self):
        panel = ReportPanel(export_after=3)
        check_export(panel)
        self.assertEqual(panel.exports, 1)

    def test_missing_control_fails(self):
        panel = ReportPanel(export_after=None)
        with self.assertRaisesRegex(LookupError, 'Export CSV'):
            check_export(panel)
        self.assertEqual(panel.exports, 0)


if __name__ == '__main__':
    unittest.main()
