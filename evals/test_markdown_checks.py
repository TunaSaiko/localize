import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import char_lint
import deliverable_check
import distribution_check as distribution
from markdown_utils import emphasis_signature, link_labels, prose_view, split_cells, table_rows


class MarkdownChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.file = Path(self.temp.name) / 'sample.md'

    def table(self, source, target):
        self.file.write_text('| id | source | target |\n|---|---|---|\n'
                             f'| row1 | {source} | {target} |\n', encoding='utf-8')
        return self.file

    def run_cli(self, script, *args):
        return subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)],
                              capture_output=True, text=True,
                              env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})

    def deliver(self, source, target):
        return self.run_cli('deliverable_check.py', self.table(source, target),
                            '--src-col', 1, '--tgt-col', 2,
                            '--source-locale', 'en-US', '--target-locale', 'ja-JP')

    def test_preserved_emphasis(self):
        for a, b in [('Use **desktop** app.', '**デスクトップ**アプリを使います。'),
                     ('**Heading**', '**見出し**'), ('__Heading__', '__見出し__'),
                     ('*Heading*', '*見出し*'), ('_Heading_', '_見出し_')]:
            with self.subTest(source=a):
                run = self.deliver(a, b)
                self.assertEqual(0, run.returncode, run.stdout + run.stderr)

    def test_added_emphasis_is_still_an_error(self):
        run = self.deliver('Use desktop app.', 'これは**追加強調**です。')
        self.assertEqual(1, run.returncode)
        self.assertIn('新增 markdown 强调', run.stdout)

    def test_changed_or_removed_emphasis(self):
        for t in ['__見出し__', '見出し']:
            with self.subTest(target=t):
                run = self.deliver('**Heading**', t)
                self.assertEqual(1, run.returncode)
                self.assertIn('不对称', run.stdout)

    def test_symmetric_markup_does_not_exempt_markers(self):
        for target in ['**見出し**【要確認】', '**見出し**（原文のまま）']:
            with self.subTest(target=target):
                run = self.deliver('**Heading**', target)
                self.assertEqual(1, run.returncode)
                self.assertIn('标记泄漏', run.stdout)

    def test_metadata_placeholders_are_still_checked(self):
        run = self.deliver('**Hello** {name}', '**こんにちは** {user}')
        self.assertEqual(1, run.returncode)
        self.assertIn('占位符不匹配', run.stdout)

    def test_original_annotations_still_fail(self):
        run = self.deliver('Brand', '**ブランド**（原文のまま）')
        self.assertEqual(1, run.returncode)
        self.assertIn('标记泄漏', run.stdout)

    def test_code_escapes_and_identifiers_are_not_emphasis(self):
        for text in ['`a*b*c`', 'file_name_key', r'\*not emphasis\*', 'https://a.example/my_file_name']:
            self.assertEqual((), emphasis_signature(text), text)

    def test_multiple_emphasis_spans(self):
        self.assertEqual(('**', '**'), emphasis_signature('**first** and **second**'))
        self.assertEqual(('**',), emphasis_signature('これは**強調**です'))

    def test_table_headers_and_line_numbers(self):
        self.file.write_text('# Title\n\n| Custom | source | target |\n|:---|---:|---|\n'
                             '| row1 | Text. | 文。 |\n', encoding='utf-8')
        self.assertEqual([(5, ['row1', 'Text.', '文。'])], list(table_rows(self.file)))
        self.assertEqual([(5, 'Text.', '文。')], distribution.rows_of(self.file, 1, 2))
        self.assertEqual(1, len(deliverable_check.parse_rows(self.file, 1, 2)[0]))

    def test_missing_header_does_not_remove_unrelated_row(self):
        self.file.write_text('| real | Text | 文 |\n\n|---|---|---|\n', encoding='utf-8')
        self.assertEqual(1, len(list(table_rows(self.file))))

    def test_separator_checks_all_cells(self):
        self.file.write_text('| - | real source | 本文 |\n', encoding='utf-8')
        self.assertEqual(1, len(list(table_rows(self.file))))

    def test_pipe_escaping_and_inline_code(self):
        self.assertEqual(['id', r'a|b', '`a|b`', '末尾|'],
                         split_cells(r'| id | a\|b | `a|b` | 末尾\| |'))

    def test_fenced_tables_are_not_document_data(self):
        self.file.write_text('```md\n| id | source | target |\n|---|---|---|\n'
                             '| code | Example | 例 |\n```\n'
                             '| id | source | target |\n|---|---|---|\n'
                             '| real | Text | 本文 |\n', encoding='utf-8')
        self.assertEqual(['real'], [c[0] for _, c in table_rows(self.file)])

    def test_link_targets_removed_labels_kept(self):
        text = '[説明(OCR)を読む](https://example.com/a_(b)?q=1)が必要です'
        self.assertEqual('説明(OCR)を読むが必要です', link_labels(text))
        self.assertEqual('動画を見る', prose_view('[![動画を見る](https://a.b/c.png)](https://d.e/?v=1)'))

    def test_url_version_and_extensions_do_not_count_as_sentences(self):
        cases = [('Read [guide](https://a.b/x?q=1).', 1),
                 ('Version v3.5.1 imports *.one files. Next!', 2),
                 ('Use file.md. Done.', 2), ('`a.b?x!`', 0),
                 ('[![image](https://a.b/a.png)](https://c.d/?v=1)', 0),
                 ('Read https://a.b/guide.', 1), ('A. B.', 2)]
        for text, count in cases:
            for locale in ('en', 'en-US', 'en_GB'):
                with self.subTest(text=text, locale=locale):
                    self.assertEqual(count, distribution.sent_breaks(text, locale))

    def test_reordered_emphasis_is_allowed(self):
        run = self.deliver('Click **Save** or *Cancel*.', '*キャンセル*または**保存**を選びます。')
        self.assertEqual(0, run.returncode, run.stdout + run.stderr)

    def test_fenced_example_not_a_deliverable(self):
        self.file.write_text('```md\n| id | source | target |\n|---|---|---|\n'
                             '| code | Example | **例** |\n```\n'
                             '| id | source | target |\n|---|---|---|\n'
                             '| real | Text | 本文 |\n', encoding='utf-8')
        result = self.run_cli('deliverable_check.py', self.file, '--target-locale', 'ja-JP',
                              '--source-locale', 'en-US', '--src-col', 1, '--tgt-col', 2)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn('检查行数: 1', result.stdout)

    def test_money_near_restoration_and_dimension_is_not_currency(self):
        for text in ['復元100%', '復元 100 件', '復元100件', '次元100', '三次元 3', '100元素']:
            self.assertEqual({}, distribution._currency_tokens(text), text)
        self.assertEqual({'CNY': 1}, distribution._currency_tokens('100元で購入'))
        self.assertEqual({'JPY': 1}, distribution._currency_tokens('100円相当'))

    def test_visible_punctuation_preserved(self):
        self.assertEqual(2, distribution.sent_breaks('読んでください。次へ！', 'ja-JP'))
        self.assertEqual('項目　補足', prose_view('- 項目　補足'))
        self.assertEqual('First. Second.', prose_view('1. First. Second.'))

    def test_currency_candidates_require_amounts(self):
        for text in ['復元方法', '元データ', '円滑', 'USD_CONFIG', '[復元](https://x.org/100元)']:
            self.assertEqual({}, distribution._currency_tokens(text), text)
        for text, code in [('100 元', 'CNY'), ('100円', 'JPY'), ('100 円', 'JPY'),
                           ('$10', 'USD'), ('USD 10', 'USD'), ('10米ドル', 'USD'),
                           ('CNY 1,000', 'CNY'), ('１００人民元', 'CNY')]:
            self.assertEqual({code: 1}, distribution._currency_tokens(text), text)
        self.assertEqual({'¥(币种待确认)': 1}, distribution._currency_tokens('¥100'))

    def test_link_parentheses_not_linted_but_label_is(self):
        opts = {'space': 'report', 'software': False}
        clean = '[ガイド](https://example.org/a_(b))を読む'
        bad = '[説明(OCR)を読む](https://example.org/a_(b))が必要です'
        clean_findings, _ = char_lint.findings_ja([clean], opts)
        bad_findings, _ = char_lint.findings_ja([bad], opts)
        self.assertFalse(any('半角括号' in row[2] for row in clean_findings))
        self.assertTrue(any('半角括号' in row[2] for row in bad_findings))
        findings, _ = char_lint.findings_ja(['説明(OCR)が必要です'], opts)
        self.assertTrue(any('半角括号' in row[2] for row in findings))

    def test_ui_character_error_not_hidden_in_link(self):
        findings, _ = char_lint.findings_ja(['[東京·大阪](https://x.org)'], {'space': 'report', 'software': False})
        self.assertTrue(any('中黑' in row[2] for row in findings))

    def test_zero_rows_and_bad_columns_are_errors(self):
        for script in ('deliverable_check.py', 'distribution_check.py'):
            self.file.write_text('# 普通 Markdown\n\n本文。\n', encoding='utf-8')
            result = self.run_cli(script, self.file, '--target-locale', 'ja', '--src-col', 1, '--tgt-col', 2)
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            for src, tgt in [(-1, 2), (1, 1), (9, 10)]:
                result = self.run_cli(script, self.table('Text', '本文'), '--target-locale', 'ja',
                                      '--src-col', src, '--tgt-col', tgt)
                self.assertEqual(2, result.returncode, result.stdout + result.stderr)

    def test_legacy_smoke(self):
        sample = ROOT / 'evals/smoke/bilingual.md'
        result = self.run_cli('deliverable_check.py', sample, '--target-locale', 'ja-JP',
                              '--source-locale', 'zh-CN', '--src-col', 1, '--tgt-col', 2)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual(7, len(distribution.rows_of(sample, 1, 2)))

    def test_fixture_cli(self):
        sample = ROOT / 'evals/smoke/markdown-document.md'
        result = self.run_cli('deliverable_check.py', sample, '--target-locale', 'ja-JP',
                              '--source-locale', 'en-US', '--src-col', 1, '--tgt-col', 2)
        self.assertEqual(1, result.returncode)
        self.assertIn('必须处理 1 项', result.stdout)
        self.assertIn('[L2]', result.stdout)
        result = self.run_cli('distribution_check.py', sample, '--target-locale', 'ja-JP',
                              '--source-locale', 'en-US', '--src-col', 1, '--tgt-col', 2)
        self.assertEqual(0, result.returncode)
        self.assertIn('解析 5 行', result.stdout)
        self.assertNotIn('| `/` |', result.stdout)
        self.assertNotIn('| `:` |', result.stdout)
        result = self.run_cli('char_lint.py', sample, '--locale', 'ja-JP', '--space', 'ms', '--tgt-col', 2)
        self.assertEqual(0, result.returncode)
        self.assertIn('取到 5 个单元格', result.stdout)


if __name__ == '__main__':
    unittest.main()
