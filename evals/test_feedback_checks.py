from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'feedback_check.py'
SOURCE = '据传闻，某头部客户计划于 2027 年上线。平台向商户收取 3% 的服务费，标准套餐售价 ¥1,200/月。'


class FeedbackChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        self.source = self.dir / 'source.md'
        self.source.write_text(SOURCE, encoding='utf-8')

    def run_check(self, pack_text, *extra, against=None):
        pack = self.dir / 'feedback-pack.md'
        pack.write_text(pack_text, encoding='utf-8')
        targets = against if against is not None else [self.source]
        return subprocess.run([sys.executable, str(SCRIPT), str(pack), '--against', *map(str, targets), *extra],
                              capture_output=True, text=True)

    def test_clean_pack_passes(self):
        result = self.run_check('| F1 | 漏报 | `传闻` 被译成 `報じられている` | 应保留传闻语气 | 个人判断 | references/pairs/zh-ja.md |')
        self.assertEqual(0, result.returncode, result.stdout)
        self.assertIn('必须处理: 0 项', result.stdout)

    def test_verbatim_sentence_fails(self):
        result = self.run_check('现象：据传闻，某头部客户计划于 2027 年上线，被译成了确定语气')
        self.assertEqual(1, result.returncode)
        self.assertIn('共有', result.stdout)

    def test_whitespace_variant_still_caught(self):
        result = self.run_check('平台 向商户\n收取 3% 的 服务费，标准套餐售价')
        self.assertEqual(1, result.returncode)

    def test_email_url_path_fail(self):
        for text in ['联系 someone@client.co.jp', '见 https://client.example.jp/plan', '文件在 /Users/alice/work/a.md']:
            with self.subTest(text=text):
                self.assertEqual(1, self.run_check(text).returncode)

    def test_repo_and_example_urls_allowed(self):
        result = self.run_check('提交到 https://github.com/TunaSaiko/localize/issues/new/choose ，示例 https://example.com/plan')
        self.assertEqual(0, result.returncode, result.stdout)

    def test_numbers_are_listed_not_failed(self):
        result = self.run_check('术语表命中 19/19，金额 ¥1,200 需确认')
        self.assertEqual(0, result.returncode, result.stdout)
        self.assertIn('¥1,200', result.stdout)

    def test_empty_against_file_is_error_not_pass(self):
        empty = self.dir / 'empty.md'
        empty.write_text('  \n', encoding='utf-8')
        result = self.run_check('干净的内容', against=[empty])
        self.assertEqual(2, result.returncode)

    def test_missing_against_file_is_error(self):
        result = self.run_check('干净的内容', against=[self.dir / 'nope.md'])
        self.assertEqual(2, result.returncode)

    def test_threshold_respected(self):
        self.assertEqual(0, self.run_check('客户计划于', '--max-run', '15').returncode)
        self.assertEqual(1, self.run_check('客户计划于', '--max-run', '4').returncode)


if __name__ == '__main__':
    unittest.main()
