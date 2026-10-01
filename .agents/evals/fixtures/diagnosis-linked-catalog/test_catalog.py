from pathlib import Path
import tempfile
import unittest
from catalog import find_cards


class PublishedCatalogTest(unittest.TestCase):
    def test_direct_linked_nested_and_cyclic_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            published = base / 'published'
            direct = published / 'groups/plain'
            direct.mkdir(parents=True)
            (direct / 'CARD.md').write_text('Plain card')
            source = base / 'library'
            (source / 'deep').mkdir(parents=True)
            (source / 'deep/CARD.md').write_text('Linked card')
            (published / 'groups/linked').symlink_to(source, target_is_directory=True)
            (source / 'back').symlink_to(published, target_is_directory=True)
            (published / 'dangling').symlink_to(base / 'absent', target_is_directory=True)
            self.assertEqual(find_cards(published), ['groups/linked/deep/CARD.md', 'groups/plain/CARD.md'])


if __name__ == '__main__':
    unittest.main()
