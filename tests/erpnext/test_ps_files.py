"""妮菈 ERPNext 試用版的 PowerShell 腳本檢查：語法正確，含中文者有 UTF-8 BOM（Windows PowerShell 5.1 才讀得對）。"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "nila-erpnext"
PS_FILES = sorted(ROOT.rglob("*.ps1"))


class TestPowerShellFiles(unittest.TestCase):
    def test_files_found(self):
        self.assertGreaterEqual(len(PS_FILES), 2)

    def test_bom_when_non_ascii(self):
        for f in PS_FILES:
            data = f.read_bytes()
            has_bom = data[:3] == b"\xef\xbb\xbf"
            non_ascii = any(b > 127 for b in data)
            self.assertTrue(not non_ascii or has_bom, f"{f.name} 含中文但沒有 UTF-8 BOM")

    def test_no_unbalanced_braces_as_quick_syntax_check(self):
        # 語法的完整檢查在 GitHub Actions（pwsh 實際執行安裝與驗證腳本）；這裡只做快速的括號與字串檢查
        for f in PS_FILES:
            text = re.sub(r"<#.*?#>|#[^\n]*", "", f.read_text(encoding="utf-8-sig"), flags=re.S)
            self.assertEqual(text.count("{") - text.count("}"), 0, f"{f.name} 大括號不成對")


if __name__ == "__main__":
    unittest.main()
