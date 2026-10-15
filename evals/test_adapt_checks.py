"""adapt 授权门与多对多事实映射的正反回归。

反例一律从 evals/smoke/adapt/ 的正例样本变异得到：只有一份事实来源，
样本改了而变异串对不上时测试会直接报「样本已漂移」，不会静默失效。
"""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'adapt_check.py'
FIXTURE = ROOT / 'evals' / 'smoke' / 'adapt'


class AdaptChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        for item in FIXTURE.iterdir():
            if item.is_file():
                shutil.copy(item, self.dir / item.name)

    # ---------------------------------------------------------------- helpers
    def edit(self, name, old, new):
        path = self.dir / name
        text = path.read_text(encoding='utf-8')
        self.assertIn(old, text, f'{name} 里找不到待替换文本，正例样本已漂移：{old!r}')
        path.write_text(text.replace(old, new, 1), encoding='utf-8')

    def resync_hash(self):
        """源文被改动的反例里，把账本与 map 的登记哈希同步过去，隔离出真正要测的那一项。"""
        digest = hashlib.sha256((self.dir / 'source.zh.md').read_bytes()).hexdigest()[:12]
        for name in ('fact-ledger.md', 'adapt-map.md'):
            path = self.dir / name
            text = path.read_text(encoding='utf-8')
            self.assertIn('64571ddac112', text, f'{name} 的源文哈希字段已漂移')
            path.write_text(text.replace('64571ddac112', digest), encoding='utf-8')

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)],
                              capture_output=True, text=True, cwd=self.dir,
                              env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})

    def gate(self, with_map=True):
        args = ['gate', '--authorization', 'authorization.md',
                '--structure', 'structure-options.md',
                '--conventions', 'market-conventions.md']
        if with_map:
            args += ['--map', 'adapt-map.md']
        return self.run_cli(*args)

    def mapping(self):
        return self.run_cli('map', '--source', 'source.zh.md', '--ledger', 'fact-ledger.md',
                            '--map', 'adapt-map.md', '--draft', 'draft.ja.md',
                            '--authorization', 'authorization.md', '--glossary', 'glossary.md')

    def assertBlocked(self, run, code, needle):
        self.assertEqual(code, run.returncode, run.stdout + run.stderr)
        self.assertIn(needle, run.stdout)

    # ------------------------------------------------------------- 授权门正例
    def test_gate_passes_with_real_author_approval(self):
        run = self.gate()
        self.assertEqual(0, run.returncode, run.stdout + run.stderr)
        self.assertIn('阻塞 0 项', run.stdout)

    # ------------------------------------------------------------- 授权门反例
    def test_gate_blocks_when_no_plan_approved(self):
        self.edit('structure-options.md', '| 批准方案 | A |', '| 批准方案 | A / B / 不批准 |')
        self.assertBlocked(self.gate(), 2, '作者未批准具体方案前不得生成')

    def test_gate_blocks_when_approval_has_no_author_event(self):
        self.edit('authorization.md',
                  '| AUTH-03 | 合并或拆分表达单元 | 全篇 | 已授权 | 作者本人 2026-09-16 |',
                  '| AUTH-03 | 合并或拆分表达单元 | 全篇 | 已授权 |  |')
        self.assertBlocked(self.gate(), 2, '模型不能自填批准')

    def test_gate_blocks_when_structure_verdict_has_no_date(self):
        self.edit('structure-options.md', '| 作者确认/日期 | 作者本人 2026-09-16 |',
                  '| 作者确认/日期 | <> |')
        self.assertBlocked(self.gate(), 2, '批准必须是真实事件')

    def test_gate_blocks_when_fact_layer_unlocked(self):
        self.edit('authorization.md', '**永远禁止**', '已授权')
        self.assertBlocked(self.gate(), 2, '事实层动作永远不可授权')

    def test_gate_blocks_unauthorized_action_referenced_by_map(self):
        self.edit('adapt-map.md', 'AUTH-03', 'AUTH-01')
        self.assertBlocked(self.gate(), 2, '但该动作未获授权')

    def test_gate_blocks_map_without_any_authorization_reference(self):
        self.edit('adapt-map.md', '市场惯例 CONV-001；AUTH-03', '市场惯例 CONV-001')
        self.assertBlocked(self.gate(), 2, '结构变化无授权依据')

    def test_gate_exempts_rows_marked_as_no_structural_change(self):
        """只是翻译、没动结构的行不该被逼着引用授权编号；但豁免必须显式写出来。"""
        self.edit('adapt-map.md', '| MAP-002 | SRC-003 | TGT-002 | 改写 | FACT-003 | 市场惯例 CONV-001；AUTH-02 | 已审 |',
                  '| MAP-002 | SRC-003 | TGT-002 | 无结构变化 | FACT-003 | 市场惯例 CONV-001 | 已审 |')
        run = self.gate()
        self.assertEqual(0, run.returncode, run.stdout + run.stderr)

    def test_gate_blocks_without_reader_matched_sample(self):
        self.edit('market-conventions.md', '| 已验证 |', '| 未验证 |')
        self.assertBlocked(self.gate(), 2, '只能停止 adapt 或降级 translate')

    def test_gate_blocks_when_map_plan_differs_from_verdict(self):
        self.edit('adapt-map.md', '批准方案：A', '批准方案：B')
        self.assertBlocked(self.gate(), 2, '与作者裁决')

    def test_gate_accepts_non_letter_plan_name_with_matching_section(self):
        """方案名不限于单个字母——真实项目里 A''、A-2、案A 都常见，只要文件里真有那一节。"""
        self.edit('structure-options.md', '## 方案 A：配额与例外合并为一段',
                  "## 方案 A''：配额与例外合并为一段")
        self.edit('structure-options.md', '| 批准方案 | A |', "| 批准方案 | A'' |")
        run = self.gate(with_map=False)
        self.assertEqual(0, run.returncode, run.stdout + run.stderr)

    def test_gate_blocks_plan_name_with_no_matching_section(self):
        self.edit('structure-options.md', '| 批准方案 | A |', '| 批准方案 | C |')
        self.assertBlocked(self.gate(with_map=False), 2, '找不到对应的')

    def test_gate_accepts_two_table_conventions(self):
        """样本单列一张表、惯例行引用 S 编号，也要认——这是真实材料上逼出来的形状。"""
        shutil.copy(self.dir / 'market-conventions.two-table.md', self.dir / 'market-conventions.md')
        run = self.gate()
        self.assertEqual(0, run.returncode, run.stdout + run.stderr)
        self.assertIn('样本表：2 份，其中可作依据 1 份', run.stdout)

    def test_gate_blocks_when_only_unusable_samples_are_referenced(self):
        """只引用了被判为「不可作依据」的翻译产物样本 → 不算有样本。"""
        shutil.copy(self.dir / 'market-conventions.two-table.md', self.dir / 'market-conventions.md')
        self.edit('market-conventions.md', '| CONV-001 | 例外条件用「ただし」接在许可句之后，同段呈现 | S1 |',
                  '| CONV-001 | 例外条件用「ただし」接在许可句之后，同段呈现 | S2 |')
        self.assertBlocked(self.gate(), 2, '只能停止 adapt 或降级 translate')

    # --------------------------------------------------------------- 映射正例
    def test_map_passes_on_two_to_one_merge(self):
        run = self.mapping()
        self.assertEqual(0, run.returncode, run.stdout + run.stderr)
        self.assertIn('阻塞 0 项', run.stdout)

    def test_map_does_not_treat_unit_count_mismatch_as_omission(self):
        run = self.mapping()
        self.assertIn('3 个源单元', run.stdout)
        self.assertIn('2 个目标单元', run.stdout)
        self.assertNotIn('漏译', run.stdout.split('单元数不等不算漏译')[1])

    # --------------------------------------------------------------- 映射反例
    def test_map_blocks_when_negation_is_dropped_in_merge(self):
        self.edit('draft.ja.md', 'ただし添付ファイルは含まれないため、添付ファイルは', '添付ファイルは')
        run = self.mapping()
        self.assertBlocked(run, 1, '添付ファイルは含まれない')
        self.assertIn('这个颗粒被丢掉了', run.stdout)

    def test_map_blocks_when_beneficiary_is_changed(self):
        self.edit('draft.ja.md', '無料プランのユーザーは', '管理者は')
        self.edit('adapt-map.md', '| FACT-001 | 主体 | 免费版用户 | TGT-001 | 無料プランのユーザー |',
                  '| FACT-001 | 主体 | 免费版用户 | TGT-001 | 管理者 |')
        self.edit('adapt-map.md', '| FACT-002 | 主体 | 免费版用户 | TGT-001 | 無料プランのユーザー |',
                  '| FACT-002 | 主体 | 免费版用户 | TGT-001 | 管理者 |')
        self.assertBlocked(self.mapping(), 1, '所指被换了')

    def test_map_blocks_when_granule_has_no_landing_row(self):
        self.edit('adapt-map.md',
                  '| FACT-002 | 否定/限制/条件 | 导出不包含附件 | TGT-001 | 添付ファイルは含まれない |\n', '')
        self.assertBlocked(self.mapping(), 1, '映射缺口')

    def test_map_blocks_when_landing_row_rewrites_ledger_value(self):
        self.edit('adapt-map.md', '| FACT-001 | 数量/单位 | 3 个 | TGT-001 | 3冊 |',
                  '| FACT-001 | 数量/单位 | 5 个 | TGT-001 | 3冊 |')
        self.assertBlocked(self.mapping(), 1, '账本是基准')

    def test_map_blocks_when_ledger_hash_is_stale(self):
        self.edit('fact-ledger.md', '64571ddac112', 'deadbeef0000')
        self.assertBlocked(self.mapping(), 1, '不能在生成后回头改')

    def test_map_blocks_unmapped_source_unit(self):
        self.edit('source.zh.md', '<!-- SRC-003 -->',
                  '<!-- SRC-004 -->\n导出的文件保留原有目录结构。\n\n<!-- SRC-003 -->')
        self.resync_hash()
        self.assertBlocked(self.mapping(), 1, '不能当作已覆盖')

    def test_map_blocks_target_unit_without_source(self):
        self.edit('draft.ja.md', '<!-- TGT-002 -->',
                  '<!-- TGT-003 -->\nサポートへのお問い合わせはこちらです。\n\n<!-- TGT-002 -->')
        self.assertBlocked(self.mapping(), 1, '没有来源')

    def test_map_blocks_number_added_to_draft(self):
        self.edit('draft.ja.md', 'エクスポート回数に制限はありません。',
                  'エクスポート回数に制限はありません。反映まで24時間かかります。')
        self.assertBlocked(self.mapping(), 1, '只在目标稿出现')

    def test_map_downgrades_added_number_that_is_a_declared_realization(self):
        """英语 two / 日语 2 —— 正则只抓阿拉伯数字，会把正常翻译误判成「加事实」。
        已在落地表声明为目标实现的，降为需人工确认，不阻塞。"""
        self.edit('draft.ja.md', 'エクスポート回数に制限はありません。', 'エクスポート回数の制限は2つともありません。')
        self.edit('adapt-map.md',
                  '| FACT-003 | 否定/限制/条件 | 不受限制 | TGT-002 | 制限はありません |',
                  '| FACT-003 | 否定/限制/条件 | 不受限制 | TGT-002 | 制限は2つともありません |')
        self.edit('adapt-map.md',
                  '| FACT-003 | 功能/价格/法律承诺 | 付费档位的解除条件 | TGT-002 | エクスポート回数に制限はありません |',
                  '| FACT-003 | 功能/价格/法律承诺 | 付费档位的解除条件 | TGT-002 | エクスポート回数の制限は2つともありません |')
        run = self.mapping()
        self.assertEqual(0, run.returncode, run.stdout + run.stderr)
        self.assertIn('已在落地表声明为某个颗粒的目标实现', run.stdout)

    def test_map_still_blocks_added_number_that_is_not_declared(self):
        self.edit('draft.ja.md', 'エクスポート回数に制限はありません。',
                  'エクスポート回数に制限はありません。反映まで24時間かかります。')
        self.assertBlocked(self.mapping(), 1, '只在目标稿出现')

    def test_map_ignores_structural_numbering_from_authorized_rewrite(self):
        """AUTH-08 授权「散文 → 编号步骤」，闸门不能拦住它自己授权的那个改写。
        编号列表和脚注记号是版式，不是事实。"""
        self.edit('draft.ja.md', 'ただし添付ファイルは含まれないため、添付ファイルは個別にダウンロードしてください。',
                  'ただし添付ファイルは含まれないため、添付ファイルは個別にダウンロードしてください。＊1\n\n'
                  '1. エクスポート画面を開きます。\n'
                  '2. ノートブックを選びます。\n\n'
                  '＊1 補足です。')
        run = self.mapping()
        self.assertEqual(0, run.returncode, run.stdout + run.stderr)

    def test_map_still_sees_numbers_inside_prose_after_stripping_markers(self):
        """剥的是行首编号和脚注记号，正文里的事实数字一个都不能漏。"""
        self.edit('draft.ja.md', '毎月3冊のノートブック', '毎月30冊のノートブック')
        run = self.mapping()
        self.assertBlocked(run, 1, '只在源文出现')
        self.assertIn('`30`', run.stdout)

    def test_map_blocks_number_lost_from_draft(self):
        self.edit('draft.ja.md', '毎月3冊のノートブック', '毎月複数冊のノートブック')
        self.assertBlocked(self.mapping(), 1, '只在源文出现')

    def test_map_blocks_when_landing_table_is_absent(self):
        path = self.dir / 'adapt-map.md'
        text = path.read_text(encoding='utf-8')
        head, _, _ = text.partition('## 事实落地表')
        path.write_text(head, encoding='utf-8')
        self.assertBlocked(self.mapping(), 1, '没有这张表就没有可机检的映射合同')

    def test_map_blocks_wrong_anchor_prefix_in_draft(self):
        """照抄源文锚点是常见手滑；必须报「锚点用错前缀」，而不是假的「目标单元无来源」。"""
        self.edit('draft.ja.md', '<!-- TGT-002 -->', '<!-- SRC-002 -->')
        run = self.mapping()
        self.assertBlocked(run, 1, '锚点用错前缀')
        self.assertNotIn('SRC-002 没有来源', run.stdout)

    def test_map_blocks_when_draft_has_no_anchors(self):
        path = self.dir / 'draft.ja.md'
        text = path.read_text(encoding='utf-8')
        path.write_text(text.replace('<!-- TGT-001 -->', '').replace('<!-- TGT-002 -->', ''),
                        encoding='utf-8')
        self.assertBlocked(self.mapping(), 1, '无法做单元级映射核对')


if __name__ == '__main__':
    unittest.main(verbosity=2)
