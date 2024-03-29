import os
import unittest
import yaml
from multivac.sensors.test_status import test_status_iter
from multivac.sensors.test_status import test_smart_status_iter


CUR_DIR = os.path.dirname(os.path.abspath(__file__))


class TestStatus(unittest.TestCase):
    def check_test_status_iter(self, log_basename):
        exp_filepath = os.path.join(CUR_DIR, '{}.yaml'.format(log_basename))
        log_filepath = os.path.join(CUR_DIR, log_basename)

        with open(exp_filepath, 'r') as f:
            exp = yaml.safe_load(f)
        with open(log_filepath, 'r') as f:
            for i, res in enumerate(test_status_iter(f)):
                self.assertEqual(list(res), exp[i])

    def check_test_smart_status_iter(self, log_basename):
        exp_filepath = os.path.join(CUR_DIR, '{}.smart.yaml'.format(
            log_basename))
        log_filepath = os.path.join(CUR_DIR, log_basename)

        with open(exp_filepath, 'r') as f:
            exp = yaml.safe_load(f)
        with open(log_filepath, 'r') as f:
            for i, res in enumerate(test_smart_status_iter(f)):
                self.assertEqual(list(res), exp[i])

    # 925099517.log has fails that are reported this way:
    #
    #  | replication/gh-6034-limbo-ownership.test.lua <..spaces..> [ fail ]
    #
    #  | replication/on_replace.test.lua <..spaces..> Test timeout of 310 secs reached<..tab..>[ fail ]

    def test_status_basic(self):
        self.check_test_status_iter('925099517.log')

    def test_smart_status_basic(self):
        self.check_test_smart_status_iter('925099517.log')

    # 900598368.log has a transient fail that is reported this way:
    #
    #  | vinyl/gh.test.lua
    #  | <...>
    #  | [ fail ]
    #  | <...>
    #  | vinyl/gh.test.lua <..spaces..> [ pass ]

    def test_status_another_line(self):
        self.check_test_status_iter('900598368.log')

    def test_smart_status_another_line(self):
        self.check_test_smart_status_iter('900598368.log')

    # 3828337083.log has a hung test (when test-run kills its
    # workers). It looks so:
    #
    #  | Test hung! Result content mismatch:
    #  | --- replication/gh-6018-election-boot-voter.result <...>
    #  | +++ /build/<...>/gh-6018-election-boot-voter.result <...>

    def test_status_hang(self):
        self.check_test_status_iter('3828337083.log')

    def test_smart_status_hang(self):
        self.check_test_smart_status_iter('3828337083.log')

    # 92247014678.log has special coloring characters:
    # ql-tap/join3.test.lua <...> [0m[0;32m[ pass ][0m

    def test_status_colored(self):
        self.check_test_status_iter('9224701468.log')

    def test_smart_status_colored(self):
        self.check_test_smart_status_iter('9224701468.log')


if __name__ == '__main__':
    unittest.main()
