import unittest

from health_media_upload import PART_SIZE


class UploadShapeTest(unittest.TestCase):
    def test_part_size_is_suitable_for_large_media(self):
        self.assertEqual(PART_SIZE, 8 * 1024 * 1024)


if __name__ == "__main__":
    unittest.main()
