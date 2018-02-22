"""
Test Checker JSON for TopLink products line.
"""

import argparse
import datetime
import enum
import functools
import json
import string

from tabulate import tabulate

import colorama


__version__ = 0.2


def fuzzy_sub(a, b):
	"""
	Returns the difference between a and b. Substraction for number.
	For strings: it returns the sum of difference between positions of the letters.
	"""
	diff = 0
	try:
		return float(a) - float(b)
	except ValueError:
		_a = str(a)
		_b = str(b)
		diff = abs(len(_a) - len(_b))
		for chr1, chr2 in zip(_a, _b):
			diff += abs(string.printable.index(chr1) - string.printable.index(chr2))
	except TypeError:
		_a = a
		_b = b
		if not isinstance(a, list):
			_a = str(a)
		if not isinstance(b, list):
			_b = str(b)
		if type(_a) != type(_b):
			diff += 1
		diff += abs(len(_a) - len(_b))
		for v1, v2 in zip(_a, _b):
			try:
				diff += abs(float(v1) - float(v2))
			except ValueError:
				diff += abs(string.printable.index(str(v1)) - string.printable.index(str(v2)))
			#diff += abs(string.printable.index(chr1) - string.printable.index(chr2))
	return diff

class CheckMode(enum.Enum):
	"""
	Check mode defined for each Expected
	"""
	ONE = 0
	MORE = 1
	NOT = 2

class Status(enum.Enum):
	"""
	Status defined for each match msg <-> expected
	"""
	OK = 0 # Msg matches expected
	MATCH_NOT_FOUND = 1 # No message matches expected
	MATCH_ERROR = 2 # A message matches expected with at least one error on a checked field
	NO_EXPECTED = 3 # A message without expected


class Message(object):
	"""
	This class manages an output message in JSON format.
	"""
	def __init__(self, json_node):
		self.name = json_node["name"]
		self.time = float(json_node["time"])
		self._fields = {k: v for k, v in json_node["message"].items()}
		self._orig = json_node


class Expected(object):
	"""
	This class manages an expected message in JSON format.
	"""
	def __init__(self, json_node):
		self.name = json_node["name"]
		self.time = float(json_node["time"])
		self.tolerance = float(json_node["tolerance"])
		self._fields = {k: v for k, v in json_node["message"].items() if k in json_node["fieldsToCheck"]}
		self.check_mode = CheckMode[json_node["checkMode"].upper()]
		self._orig = json_node
		self._matched = None

	def fields(self):
		"""
		Generator to iterate on fields of `self`
		"""
		for pair in self._fields.items():
			yield pair


class Match(object):
	"""
	This class represents a matching between a Output object and Expected object.
	"""
	def __init__(self, message, expected):
		"""
		Constructor.
		Constructs a Match object embedding ``message`` and its ``expected``
		"""
		self.score = 0
		if expected is not None:
			self.msg = None
			self.expected = expected
			if message is not None:
				self.msg = message
				self.expected = expected
				for k, v in self.expected.fields():
					if k not in self.msg._fields:
						try:
							self.score += abs(float(v))
						except (ValueError, TypeError):
							self.score += len(v) + 1
					elif self.msg._fields[k] != v:
						self.score += fuzzy_sub(self.msg._fields[k], v)
						# try:
						# 	self.score += abs(float(self.msg._fields[k]) - float(v))
						# except (ValueError, TypeError):
						# 	if 
						# 	self.score += abs(len(self.msg._fields[k]) - len(str(v))) + 1
			else:
				if self.expected.check_mode != CheckMode.NOT:
					self.score = -2
				else:
					self.score = 0
		else:
			self.msg = message
			self.expected = None
			self.score = -1



	def __lt__(self, other):
		"""
		Returns True if `self` is less than `other`. Returns false otherwise.
		"""
		if self.msg is not None and other.msg is not None:
			if self.score == other.score:
				return self.msg.time < other.msg.time
			return self.score < other.score
		return self.expected.time < other.expected.time

	def status(self):
		"""
		Returns a Status corresponding to the matching score
		"""
		if self.score == 0:
			return Status.OK
		elif self.score == -1:
			return Status.NO_EXPECTED
		elif self.score == -2:
			return Status.MATCH_NOT_FOUND
		return Status.MATCH_ERROR

	def __repr__(self): # pragma: no cover
		"""
		Returns a string repr of `self`
		"""
		fields = list()
		data_output = None
		data_expected = None
		msg = self.msg._fields if self.msg else dict()
		expected = self.expected._fields if self.expected else dict()
		fields = sorted(list(set(list(msg.keys()) + list(expected.keys()))))

		def colored_red(key):
			"""
			Returns a formated text for `key`.
			"""
			if key not in self.msg._fields:
				return colorama.Fore.MAGENTA + colorama.Style.BRIGHT + "???" + colorama.Style.RESET_ALL
			elif (key in expected) and (msg[key] != expected[key]):
				return colorama.Fore.RED + str(msg[key]) + colorama.Style.RESET_ALL
			elif (key in expected) and (msg[key] == expected[key]):
				return colorama.Fore.GREEN + str(msg[key]) + colorama.Style.RESET_ALL
			return str(msg[key])

		default_expected = lambda k: expected[k] if k in expected else "-"

		title = lambda l: [colorama.Style.BRIGHT + f + colorama.Style.RESET_ALL for f in l]
		tab = functools.partial(tabulate, headers=title(['', 'Time', 'Name'] + fields), numalign='left', stralign='left')

		if self.expected is None:
			data_output = ['Output', self.msg.time, self.msg.name] + [colored_red(k) for k in fields]
			s = colorama.Fore.CYAN + "This Output has no expected\n" + colorama.Style.RESET_ALL
			s += str(tab([data_output]))
			return s

		if self.msg is None:
			if self.expected.check_mode == CheckMode.ONE:
				data_expected = ['Expected', self.expected.time, self.expected.name] + [default_expected(k) for k in fields]
				s = colorama.Fore.RED + "No output for this required expected \n" + colorama.Style.RESET_ALL
				s += str(tab([data_expected]))
				return s
			data_expected = ['Expected', self.expected.time, self.expected.name] + [default_expected(k) for k in fields]
			s = colorama.Fore.GREEN + "No output for this rejected expected \n" + colorama.Style.RESET_ALL
			s += str(tab([data_expected]))
			return s

		if self.expected and self.msg and self.score not in (0, -1):
			data_output = ['Output', self.msg.time, self.msg.name] + [colored_red(k) for k in fields]
			data_expected = ['Expected', self.expected.time, self.expected.name] + [default_expected(k) for k in fields]
			s = colorama.Fore.RED + "Output does not match Expected\n" + colorama.Style.RESET_ALL
			s += str(tab([data_expected, data_output]))
			return s

		data_output = ['Output', self.msg.time, self.msg.name] + [colored_red(k) for k in fields]
		data_expected = ['Expected', self.expected.time, self.expected.name] + [default_expected(k) for k in fields]
		s = ""
		if self.expected.check_mode == CheckMode.NOT:
			s = colorama.Fore.RED + "Rejected Expected matches this Output \n" + colorama.Style.RESET_ALL
		else:
			s = colorama.Fore.GREEN + "Expected matches this Output \n" + colorama.Style.RESET_ALL
		s += str(tab([data_expected, data_output]))
		return s


	def to_xml(self): # pragma: no cover
		"""
		Converts `self` to a XML Node
		"""
		status = {Status.OK: "MESSAGE MATCHED",
            Status.MATCH_NOT_FOUND: "EXPECTED WITHOUT MESSAGE",
            Status.MATCH_ERROR: "MESSAGE NOT MATCHED",
            Status.NO_EXPECTED: "MESSAGE UNCHECKED"
		         }[self.status()]
		name = self.expected.name if self.expected else self.msg.name
		interface = "JSON"
		time_from = self.expected.time if self.expected else self.msg.time
		time_to = time_from + self.expected.tolerance if self.expected else 0
		return """
	<Message>
		<Status>{status}</Status>
		<Name>{name}</Name>
		<Interface>{interface}</Interface>
		<From>{frm}</From>
		<To>{to}</To>
	</Message>""".format(
            status=status,
            name=name,
            interface=interface,
            frm=datetime.datetime.fromtimestamp(time_from/1000).strftime('%H:%M:%S.%f'),
            to=datetime.datetime.fromtimestamp(time_to/1000).strftime('%H:%M:%S.%f'))

def _fuzzy_compare(src, potential_matches):
	"""
	Compares the `src` (an Expected) to a list of potential matching Messages.
	It will return a list of Message that match or aim to match the `src`
	"""
	all_fields_src = src._fields.values()
	diff = list()
	for msg in potential_matches:
		all_fields_msg = msg._fields.values()
		dist = sum(d * 10 ** (3 - pos) for pos, d in enumerate(map(fuzzy_sub, all_fields_src, all_fields_msg)))
		if dist != 0:
			if src.check_mode != CheckMode.NOT:
				diff.append((dist, msg))
		else:
			diff.append((dist, msg))

	return [x[1] for x in sorted(diff, key=lambda a: abs(a[0]))]


class Checker(object):
	"""
	The `Checker` is used to check a list of JSON messages with a list of JSON Expecteds.
	"""
	def __init__(self):
		"""
		Constructors.
		"""
		colorama.init()
		self.retained = list()
		self.status = False

	def check(self, json_expected, json_output, filename_report, verbose=False):
		"""
		Checks if the elements in `json_expected` match elements in `json_output`.
		Returns 0 if OK. Returns -1 otherwise.

		see also self.status
		"""
		self.status = False
		self.retained = list()
		def in_tolerance(exp, msg):
			"""
			Returns True if msg is in bounds of exp relative to its tolerance.
			"""
			return ((exp.time - exp.tolerance) <= msg.time <= (exp.time + exp.tolerance)) and (exp.name == msg.name)

		assoc = list()
		for e in json_expected:
			msg_list = [o for o in json_output if in_tolerance(e, o)]
			diff_list = _fuzzy_compare(e, msg_list)
			if diff_list:
				for diff in diff_list:
					assoc.append(Match(diff, e))
			else:
				assoc.append(Match(None, e))

		left_outputs = json_output
		left_expecteds = json_expected

		for a in sorted(assoc):
			if a.msg is not None and (a.msg in [x.msg for x in self.retained]):
				continue
			elif a.expected in [x.expected for x in self.retained]:
				continue

			if a.msg and a.msg in left_outputs:
				m = a.msg
				left_outputs.remove(a.msg)
			else:
				m = None

			e = a.expected
			left_expecteds.remove(a.expected)
			self.retained.append(Match(m, e))

		for msg in left_outputs:
			if msg not in [x.msg for x in self.retained]:
				self.retained.append(Match(msg, None))

		for e in left_expecteds:
			self.retained.append(Match(None, e))

		self.retained = sorted(self.retained, key=lambda x: x.msg.time if x.msg is not None else x.expected.time)

		result = 0

		for match in self.retained:
			if match.score not in (0, -1):
				result = -1
			if verbose:
				print(match, "\n")
		self.status = result == 0

		if filename_report:
			self.to_xml(filename_report)

		return result

	def to_xml(self, filename): # pragma: no cover
		"""
		Writes Matching of `self` in `filename` as xml content.
		"""
		with open(filename, 'w') as fh:
			fh.write('<?xml version="1.0" encoding="utf-8"?>\n')
			fh.write("<Check>")
			for match in self.retained:
				fh.write(match.to_xml())
			fh.write("</Check>\n")

def _main(): # pragma: no cover
	parser = argparse.ArgumentParser(description="Test Checker JSON Version {}".format(__version__))
	parser.add_argument('-e', '--expected', type=str, help='Expected filename', required=True)
	parser.add_argument('-r', '--record', type=str, help='Messages record filename', required=True)
	parser.add_argument('-o', '--output', type=str, help='Put the reporting here', required=True)
	parser.add_argument('-v', '--verbose', default=False, action='store_true', help='Display a report', required=False)
	args = parser.parse_args()

	msgs_expected = [Expected(n) for n in json.load(open(args.expected))]
	msgs_output = [Message(n) for n in json.load(open(args.record))]

	chk = Checker()
	result = chk.check(json_expected=msgs_expected, json_output=msgs_output, filename_report=args.output, verbose=args.verbose)
	exit(result)

if __name__ == "__main__": # pragma: no cover
	_main()
