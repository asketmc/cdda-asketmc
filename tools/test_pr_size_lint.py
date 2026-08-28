#!/usr/bin/env python3

import unittest

from tools.pr_size_lint import classify, parse_numstat


class PullRequestSizeLintTest(unittest.TestCase):
    def test_counts_additions_and_deletions_but_not_binary_files(self) -> None:
        numstat = "200\t201\tsrc/a.cpp\n10\t5\ttests/a.cpp\n-\t-\tgfx/a.png\n"
        self.assertEqual(parse_numstat(numstat), (416, 2, 1))

    def test_thresholds(self) -> None:
        self.assertEqual(classify(400), "ok")
        self.assertEqual(classify(401), "warning")
        self.assertEqual(classify(799), "warning")
        self.assertEqual(classify(800), "oversize")


if __name__ == "__main__":
    unittest.main()
