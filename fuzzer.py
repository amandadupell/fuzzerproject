#!/usr/bin/env python36

# Useful functions for dealing with files and file paths
import sys, os

# Deals with the command line arguments to the fuzzer
import argparse

# Used for parsing the model specification XML file
import xml.etree.ElementTree as ET

# Utility function for printing "pretty" lists, tuples, etc.
import pprint

# Extremely useful functions in here ;)
import itertools

# Why would we need this module?
import subprocess


# Loads the model specification from a given XML file.
# No need to modify this function.
def load_model(xml_file):
    try:
        tree = ET.parse(xml_file)
    except:
        print('Error: Unable to parse the given XML file. Perhaps it has a syntax error?')
        sys.exit(-1)

    root = tree.getroot()

    optional_args = []
    positional_args = []

    opts = root.find('options')
    if opts:
        for opt in opts.iter('option'):
            optional_args.append((opt[0].text, opt[1].text))

    pos = root.find('positional')
    if pos:
        for arg in pos.iter('arg'):
            positional_args.append(arg[0].text)

    return optional_args, positional_args


# Exit the fuzzer if a non-existent file is passed in as a command line argument
# No need to modify this function.
def ensure_file_existence(file_path):
    if not os.path.isfile(file_path):
        print('Error: the file {} does not exist. Please check the path'.format(file_path))
        sys.exit(-1)


# Handle the command line arguments for the fuzzer.
# No need to modify this function.
def handle_cmd_line():
    parser = argparse.ArgumentParser()
    parser.add_argument("config")
    parser.add_argument("binary")
    args = parser.parse_args()

    if not args.config.endswith('.xml'):
        print('Error: the first parameter should end in an .xml extension')
        sys.exit(-1)

    ensure_file_existence(args.config)
    ensure_file_existence(args.binary)

    if not os.access(args.binary, os.X_OK):
        print('Error: {} is not executable'.format(args.binary))
        sys.exit(-1)

    return args


def powerset(iterable):
    s = list(iterable)
    return list(itertools.chain.from_iterable(itertools.combinations(s, r) for r in range(len(s) + 1)))


def sub_lists(list1):
    sublist = []
    for i in range(len(list1) + 1):
        sub = list1[0:i]
        sublist.append(sub)
    return sublist

# For null type, defaults to a None value
LoNullTypes = [None, ]

# For integer type, defaults to one of these int values from this list
LoIntTypes = ["-65000", "-1", "-0.25", "0", "0.25", "1", "65000", "a"]

# For string type, defaults to one of these string values from this list
LoStrTypes = ["", " ", "!@#$%^&*()/?", "\\", "\n", "1", 'a' * 2048, "/"]

# Dictionary that maps values to each other
TYPES = {'null': LoNullTypes, 'string': LoStrTypes, 'integer': LoIntTypes}

# How to determine for the error
ERROR = 'Traceback (most recent call last):'

# Deal with the command line. The parameter values will be available in
# args.config and args.binary.
args = handle_cmd_line()

# Load the model specification.
optArgs, posArgs = load_model(args.config)

# Creates a powerset of all optional arguments.
list_of_opt_args = powerset(optArgs)

# Creates all sublists for positional arguments.
list_of_pos_args = sub_lists(posArgs)

# Empty list that will be full of possible pairs of positional and optional arguments.
partial_commandlines = []

# Adds optional and positional arguments by pairs to a "partial commandline".
for opt in list_of_opt_args:
    for pos in list_of_pos_args:
        partial_commandlines.append([opt, pos])

# For every optional and positional argument in the partial commandline, get the name and type of all
# opt in opts and extend pargs to account for positional arguments.
i = 0
for opts, pargs in partial_commandlines:
    name = [opt[0] for opt in opts]
    typs = [opt[1] for opt in opts]
    typs.extend(pargs)
    # Substitute get the value associated with the type list
    val_types = [TYPES[t] for t in typs]
    # Uses itertools to produce the product of all possible value combinations.
    for val_types in itertools.product(*val_types):
        # Name of program.
        commandline = [args.binary]
        # Uses itertools zip longest to handle combining the names of optional arguments with value types and
        # replacing None values with ''.
        commandline.extend(itertools.chain.from_iterable(itertools.zip_longest(name, val_types, fillvalue='')))
        commandline = [a for a in commandline if a]
        # Adds to the count of tested commandlines.
        i += 1
        # Run subprocess with the commandline, placing each commandline on a new line
        sub = subprocess.run(commandline, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        # Catches the Traceback error caused by a commandline
        if ERROR in sub.stderr or ERROR in sub.stdout:
            print(' '.join(commandline))

# Prints the amount of tested commandlines for a program.
print('Tested {} commandlines for the program {}'.format(str(i), args.binary))
