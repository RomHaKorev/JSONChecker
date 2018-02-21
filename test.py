import copy
import inspect
import json
import os
import re
import test_checker
import unittest

from pylint import epylint as lint
from test_checker import Expected, Message, Status


class TestBasics(unittest.TestCase):
	COMBINATORIAL_EXPECTEDS = list()
	COMBINATORIAL_OUTPUTS = list()
	COMBINATORIAL_RESULTS = list()

	def check_test(self, expected, output, results, status, display=False, combin=True):

		if combin:
			self.__class__.COMBINATORIAL_EXPECTEDS += copy.deepcopy(expected)
			self.__class__.COMBINATORIAL_OUTPUTS += copy.deepcopy(output)
			self.__class__.COMBINATORIAL_RESULTS += copy.deepcopy(results)
		self.assertEqual(self.chk.check(json_expected=expected, json_output=output, filename_report=None, verbose=display), status)
		self.assertEqual([r.status() for r in self.chk.retained], results)
		#print(inspect.stack()[1][3])


	def setUp(self):
		self.chk = test_checker.Checker()
		self.maxDiff = None

	def test_001_ok(self):
		expected = [Expected({"message": {"Field_1": 1, "Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 1000,
			"checkMode": "one",
			"fieldsToCheck": ["Field_1"],
			"tolerance": "100"})]
		output = [Message({"message": {"Field_1": 1, "Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 1000})]
		results = [Status.OK]
		self.check_test(expected, output, results, 0)

	def test_002_ok_multiple_fields(self):
		expected = [Expected({"message": {"Field_1": 1, "Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 2000,
			"checkMode": "one",
			"fieldsToCheck": ["Field_1", "Field_2"],
			"tolerance": "100"})]
		output = [Message({"message": {"Field_1": 1, "Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 2000})]

		results = [Status.OK]
		self.check_test(expected, output, results, 0)
		

	def test_003_ok_multiple_fields_unchecked_fields_diff(self):
		expected = [Expected({"message": {"Field_1": 1, "Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 3000,
			"checkMode": "one",
			"fieldsToCheck": ["Field_1", "Field_2"],
			"tolerance": "100"})]
		output = [Message({"message": {"Field_1": 1, "Field_2": 2, "Field_3": 1567},
			"name": "msg_1",
			"time": 3000})]
		results = [Status.OK]
		self.check_test(expected, output, results, 0)

	def test_004_ok_more_fields_in_output(self):
		expected = [Expected({"message": {"Field_1": 1, "Field_2": 2},
			"name": "msg_1",
			"time": 4000,
			"checkMode": "one",
			"fieldsToCheck": ["Field_1", "Field_2"],
			"tolerance": "100"})]
		output = [Message({"message": {"Field_1": 1, "Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 4000})]
		results = [Status.OK]
		self.check_test(expected, output, results, 0)

	def test_005_ok_diff_no_checked(self):
		expected = [Expected({"message": {"Field_1": 1, "Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 5000,
			"checkMode": "one",
			"fieldsToCheck": ["Field_1"],
			"tolerance": "100"})]
		output = [Message({"message": {"Field_1": 1, "Field_2": 122, "Field_3": 3.4},
			"name": "msg_1",
			"time": 5000})]
		results = [Status.OK]
		self.check_test(expected, output, results, 0)

	def test_006_match_with_error(self):
		expected = [Expected({"message": {"Field_1": 1, "Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 6000,
			"checkMode": "one",
			"fieldsToCheck": ["Field_1"],
			"tolerance": "100"})]
		output = [Message({"message": {"Field_1": 10, "Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 6000})]
		results = [Status.MATCH_ERROR]
		self.check_test(expected, output, results, -1)


	def test_007_match_with_error_str(self):
		expected = [Expected({"message": {"Field_1": "Booh", "Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 7000,
			"checkMode": "one",
			"fieldsToCheck": ["Field_1"],
			"tolerance": "100"})]
		output = [Message({"message": {"Field_1": "Bah", "Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 7000})]
		results = [Status.MATCH_ERROR]
		self.check_test(expected, output, results, -1)

	def test_008_no_relevant_expected(self):
		expected = []
		output = [Message({"message": {"Field_1": 10, "Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 8000})]
		results = [Status.NO_EXPECTED]
		self.check_test(expected, output, results, 0)

	def test_009_no_matching_output(self):
		expected = [Expected({"message": {"Field_1": 1, "Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 9000,
			"checkMode": "one",
			"fieldsToCheck": ["Field_1"],
			"tolerance": "100"})]
		output = []
		results = [Status.MATCH_NOT_FOUND]
		self.check_test(expected, output, results, -1)

	def test_010_matching_output_outside_tolerance(self):
		expected = [Expected({"message": {"Field_1": 1, "Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 10000,
			"checkMode": "one",
			"fieldsToCheck": ["Field_1"],
			"tolerance": "100"})]
		output = [Message({"message": {"Field_1": 1, "Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 10500})]
		results = [Status.MATCH_NOT_FOUND, Status.NO_EXPECTED]
		self.check_test(expected, output, results, -1)

	def test_011_2_expecteds_for_1_message(self):
		expected = [Expected({"message": {"Field_1": 1, "Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 11000,
			"checkMode": "one",
			"fieldsToCheck": ["Field_1"],
			"tolerance": "400"}),
		Expected({"message": {"Field_1": 1, "Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 11100,
			"checkMode": "one",
			"fieldsToCheck": ["Field_1"],
			"tolerance": "400"})]
		output = [Message({"message": {"Field_1": 1, "Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 11200}), ]
		self.check_test(expected, output, [Status.MATCH_NOT_FOUND, Status.OK], -1)
		
	def test_012_1_expected_for_2_messages(self):
		expected = [Expected({"message": {"Field_1": 1, "Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 12000,
			"checkMode": "one",
			"fieldsToCheck": ["Field_1"],
			"tolerance": "400"})]
		output = [Message({"message": {"Field_1": 1, "Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 12100}), 
			Message({"message": {"Field_1": 1, "Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 12150})]
		self.check_test(expected, output, [Status.OK, Status.NO_EXPECTED], 0, combin=False)

	def test_013_1_expected_for_2_messages_same_time(self):
		expected = [Expected({"message": {"Field_1": 1, "Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 13000,
			"checkMode": "one",
			"fieldsToCheck": ["Field_1"],
			"tolerance": "400"})]
		output = [Message({"message": {"Field_1": 1, "Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 13100}), 
			Message({"message": {"Field_1": 1, "Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 13100})]
		self.check_test(expected, output, [Status.OK, Status.NO_EXPECTED], 0)

	def test_014_missing_num_field(self):
		expected = [Expected({"message": {"Field_1": 1, "Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 14000,
			"checkMode": "one",
			"fieldsToCheck": ["Field_1"],
			"tolerance": "100"})]
		output = [Message({"message": {"Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 14000})]
		self.check_test(expected, output, [Status.MATCH_ERROR], -1)

	def test_015_missing_str_field(self):
		expected = [Expected({"message": {"Field_1": "Booh", "Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 15000,
			"checkMode": "one",
			"fieldsToCheck": ["Field_1"],
			"tolerance": "100"})]
		output = [Message({"message": {"Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 15000})]
		self.check_test(expected, output, [Status.MATCH_ERROR], -1)

	def test_016_ok_with_not_no_message(self):
		expected = [Expected({"message": {"Field_1": 1, "Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 16000,
			"checkMode": "not",
			"fieldsToCheck": ["Field_1"],
			"tolerance": "100"})]
		output = [Message({"message": {"Field_1": 1, "Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 16000})]
		self.check_test(expected, output, [Status.OK], 0)

	def test_017_ok_with_not_no_matching_message(self):
		expected = [Expected({"message": {"Field_1": 1, "Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 17000,
			"checkMode": "not",
			"fieldsToCheck": ["Field_1"],
			"tolerance": "100"})]
		output = [Message({"message": {"Field_1": 21, "Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 17000})]
		self.check_test(expected, output, [Status.OK, Status.NO_EXPECTED], 0)
		
	def test_018_ko_with_not(self):
		expected = [Expected({"message": {"Field_1": 1, "Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 18000,
			"checkMode": "not",
			"fieldsToCheck": ["Field_1"],
			"tolerance": "100"})]
		output = [Message({"message": {"Field_1": 1, "Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 18000})]
		self.check_test(expected, output, [Status.OK], 0)

	def test_019_2_no_matching_messages_2nd_closier(self):
		expected = [Expected({"message": {"Field_1": 1, "Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 19000,
			"checkMode": "one",
			"fieldsToCheck": ["Field_1"],
			"tolerance": "400"})]
		output = [Message({"message": {"Field_1": 10, "Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 19100}), 
			Message({"message": {"Field_1": 7, "Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 19200})]
		self.check_test(expected, output, [Status.NO_EXPECTED, Status.MATCH_ERROR], -1)

	def test_020_2_expected_no_messages_wrong_order(self):
		expected = [Expected({"message": {"Field_1": 1, "Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 20500,
			"checkMode": "one",
			"fieldsToCheck": ["Field_1"],
			"tolerance": "1"}),
		Expected({"message": {"Field_1": 1, "Field_2": 2, "Field_3": 3.4},
			"name": "msg_1",
			"time": 20000,
			"checkMode": "one",
			"fieldsToCheck": ["Field_1"],
			"tolerance": "1"})]
		output = []
		self.check_test(expected, output, [Status.MATCH_NOT_FOUND, Status.MATCH_NOT_FOUND], -1)
		self.assertEqual([r.expected.time for r in self.chk.retained], [20000, 20500])

	def test_999_combinatorics(self):
		self.check_test(TestBasics.COMBINATORIAL_EXPECTEDS, TestBasics.COMBINATORIAL_OUTPUTS, TestBasics.COMBINATORIAL_RESULTS, -1, combin=False)


	def test_000_pylint(self):
		(pylint_stdout, _) = lint.py_run(os.path.join(os.path.dirname(__file__), "test_checker.py"), return_std=True)
		output = pylint_stdout.read()
		m = re.search("Your code has been rated at (.+?)/10", output)
		self.assertNotEqual(m, None)
		self.assertEqual(float(m.group(1)), 10.0)
		return False



if __name__ == '__main__':
	unittest.main()
	# suite = unittest.TestLoader().loadTestsFromTestCase(TestBasics)
	# unittest.TextTestRunner(verbosity=1).run(suite)