import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from anima_prompter.prompter import AnimaPrompt, extract_json, image_data_url_from_bytes


class TestAnimaPrompter(unittest.TestCase):
    def test_extract_json_from_clean_payload(self):
        payload = {"subject": "1girl", "tags": ["smile"]}
        self.assertEqual(extract_json(json.dumps(payload)), payload)

    def test_extract_json_from_markdown_fence(self):
        self.assertEqual(extract_json('```json\n{"subject":"1girl"}\n```'), {"subject": "1girl"})

    def test_extract_json_from_wrapped_text(self):
        text = 'Here is the JSON:\n{"subject":"1boy","tags":["coat"]}\nDone.'
        self.assertEqual(extract_json(text), {"subject": "1boy", "tags": ["coat"]})

    def test_prompt_build_string_formats_fields(self):
        prompt = AnimaPrompt(
            subject="1girl",
            artists=["artist_a", "@artist_b"],
            tags=["long_hair", "blue_eyes"],
            natural_language="She stands in the rain.",
        )
        result = prompt.build_string()
        self.assertIn("@artist_a", result)
        self.assertIn("@artist_b", result)
        self.assertIn("long hair", result)
        self.assertIn("blue eyes", result)
        self.assertIn("She stands in the rain.", result)

    def test_prompt_build_string_includes_period_and_safety(self):
        prompt = AnimaPrompt(subject="1girl", period="recent", safety="sensitive")
        result = prompt.build_string()
        self.assertTrue(result.startswith("recent,"), f"Expected 'recent' first, got: {result}")
        self.assertIn("sensitive", result)

    def test_prompt_build_string_specific_year_period(self):
        prompt = AnimaPrompt(subject="1girl", period="year 2023", safety="safe")
        result = prompt.build_string()
        self.assertIn("year 2023", result)

    def test_prompt_build_string_defaults(self):
        prompt = AnimaPrompt(subject="1girl")
        result = prompt.build_string()
        self.assertIn("newest", result)
        self.assertIn("safe", result)

    def test_image_data_url_uses_png_mime(self):
        data_url = image_data_url_from_bytes(b"abc", "reference.png")
        self.assertTrue(data_url.startswith("data:image/png;base64,"))


if __name__ == "__main__":
    unittest.main()
