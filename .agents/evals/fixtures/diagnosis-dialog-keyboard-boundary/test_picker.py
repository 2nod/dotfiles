import unittest

from picker import Picker


class PickerKeyboardTests(unittest.TestCase):
    def test_key_in_open_picker_stays_within_dialog(self):
        picker = Picker()
        picker.handle_key('F4', from_picker=True)
        self.assertEqual(picker.workspace_keys, [])
        self.assertTrue(picker.open)

    def test_escape_in_picker_dismisses_before_stopping_propagation(self):
        picker = Picker()
        picker.handle_key('Escape', from_picker=True)
        self.assertFalse(picker.open)
        self.assertEqual(picker.workspace_keys, [])

    def test_workspace_key_outside_picker_is_delivered(self):
        picker = Picker()
        picker.handle_key('Escape', from_picker=True)
        picker.handle_key('F4', from_picker=False)
        self.assertEqual(picker.workspace_keys, ['F4'])


if __name__ == '__main__':
    unittest.main()
