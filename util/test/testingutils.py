import sys, os, types, doctest
from StringIO import StringIO
from unittest import *

from pymel import lastFormattedException
import pymel.util
from pymel.util import warn

TEST_MAIN_FUNC_NAME = "test_main"
SUITE_FUNC_NAME = "suite"

def doctestFriendly(func):
    """
    Decorator which prepares maya to run doctests.
    """
    def prepForDoctest(*args, **kwargs):
        result = None
        if (sys.displayhook != sys.__displayhook__
            or sys.stdout != sys.__stdout__):
            save_displayhook = sys.displayhook
            # reset doctest.master, so we don't get spammed with
            # *** DocTestRunner.merge: '...' in both testers; summing outcomes.
            # messages...
            try:
                savedMaster = doctest.master
            except AttributeError:
                savedMaster = None

            # Note - for python 2.4 (ie, maya 8.5) compatability, can't use
            # try/except/raise - must separate
            try:
                sys.displayhook = sys.__displayhook__
                doctest.master = None
                try:
                    result = func(*args, **kwargs)
                except:
                    raise
            finally:
                sys.displayhook = save_displayhook
                doctest.master = savedMaster
        else:
            result = func(*args, **kwargs)
        return result
    return prepForDoctest
        
@doctestFriendly
def doctestmod(*args, **kwargs):
    """
    Wrapper for doctest.testmod that works in maya gui.
    """
    return doctest.testmod(*args, **kwargs)

class MayaTestRunner(TextTestRunner):
    def __init__(self, stream=sys.stdout, descriptions=True, verbosity=2):
        super(MayaTestRunner, self).__init__(stream=stream,
                                             descriptions=descriptions,
                                             verbosity=verbosity)
    
    @doctestFriendly
    def run(self, *args, **kwargs):
        super(MayaTestRunner, self).run(*args, **kwargs)
    
def default_suite(module):
    """
    Creates a suite out of all found unittests AND doctests found in the module.
    """
    theSuite = findTestCases(module)
    try:
        doctests = doctest.DocTestSuite(module)
    except ValueError:
        # will raise a value error if it found no tests...
        pass
    else:
        if doctests.countTestCases():
            theSuite.addTest(doctests)
    return theSuite

def addFuncToModule(func, module):
    if not hasattr(module, func.__name__):
        setattr(module, func.__name__, func) 

def startsWithdoubleUnderscore(testcase):
    return testcase.__name__.startswith("__")
    
def setupUnittestModule(moduleName, suiteFuncName = SUITE_FUNC_NAME, testMainName=TEST_MAIN_FUNC_NAME,
                        filterTestCases=startsWithdoubleUnderscore):
    """
    Add basic unittest functions to the given module.
     
    Will add a 'suite' function that returns a suite object for the module,
    and a 'test_main' function which runs the suite.
    
    If a filterTestCases function is given, then this is applied to all objects in the module which
    inherit from TestCase, and if it returns true, removes them from the module dictionary,
    so that they are not automatically loaded.
    
    By default, it will filter all TestCases whose name starts with a double-underscore, ie
    '__AbstractTestCase' 
    
    Will then call 'test_main' if moduleName == '__main__'
    """
    module = sys.modules[moduleName]
    def suite():
        return default_suite(module)
    suite.__name__ = suiteFuncName
    
    def test_main():
        return MayaTestRunner().run(suite())
    test_main.__name__ = testMainName
    
    addFuncToModule(suite, module)
    addFuncToModule(test_main, module)
    
    for name in dir(module):
        obj = getattr(module, name)
        if (isinstance(obj, (type, types.ClassType)) and
            issubclass(obj, TestCase) and
            filterTestCases and
            filterTestCases(obj)):
            delattr(module, name)
    
    if moduleName == '__main__':
        test_main()

# Make this import / initialize pymel!
#class MayaTestRunner(TextTestRunner):
#    '''
#    Test runner for unittests that require maya.
#    '''
#    
#    # For now, just calls standard TextTestRunner with different defaults
#    def __init__

class TestCaseExtended(TestCase):
    # Set this to True if you want to create a TestCase that you DON'T
    # want run (ie, an abstract class you wish to derive from, etc)
    DO_NOT_LOAD = False
    
    #def addTestFunc(self, function):
    def assertNoError(self, function, *args, **kwargs):
        try:
            function(*args, **kwargs)
        except:
            self.fail("Exception raised:\n%s" % lastFormattedException())
    
    def assertIteration(self, iterable, expectedResults,
                        orderMatters=True,
                        onlyMembershipMatters=False):
        """
        Asserts that the iterable yields the expectedResults.
        
        'expectedResults' should be a sequence of items, where each item matches
        an item returned while iterating 'iterable'.

        If onlyMembershipMatters is True, then as long as the results of
        iterable are containined within expectedResults, and every member of
        expectedResults is returned by iterable at least once, the test will
        pass. (Ie, onlyMembershipMatters will override orderMatters.)
        
        If onlyMembershipMatters is False and orderMatters is True, then the
        items in expectedResults should match the order of items returned by the
        iterable.

        If onlyMembershipMatters is False and orderMatters is False, the
        assertion will pass as long as there is a one-to-one correspondence
        between the items of expectedResults and the items returned by
        iterable. Note that in this case, duplicate return values from the
        iterable will still need duplicate results in the expectedResults.

        Examples:

        # orderMatters=True, onlyMembershipMatters=False by default

        #################################################
        ## orderMatters=True, onlyMembershipMatters=False
        #################################################

        # will PASS
        assertIteration( "foo", ['f', 'o', 'o'])

        # will FAIL - last 'o' not present in expectedResults
        assertIteration( "foo", ['f', 'o'])

        # will FAIL - 'x' not present in iterable
        assertIteration( "foo", ['f', 'o', 'o', 'x'])

        # will FAIL - order incorrect
        assertIteration( "foo", ['o', 'f', 'o'])

        #################################################

        
        
        #################################################
        ## orderMatters=True, onlyMembershipMatters=True
        #################################################

        # will PASS - if onlyMembershipMatters, duplicate entries are ignored
        assertIteration( "foo", ['f', 'o', 'o'], onlyMemberShipMatters=True)        

        #will PASS
        assertIteration( "foo", ['f', 'o'], onlyMemberShipMatters=True)

        #will FAIL - 'o' not present in expectedResults
        assertIteration( "foo", ['f'], onlyMemberShipMatters=True)

        # will FAIL - 'x' not present in iterable
        assertIteration( "foo", ['f', 'o', 'x'], onlyMemberShipMatters=True)

        # will PASS - order irrelevant
        assertIteration( "foo", ['o', 'f', 'o'], onlyMemberShipMatters=True)        
        #################################################


        
        #################################################
        ## orderMatters=False, onlyMembershipMatters=False
        #################################################

        # will PASS
        assertIteration( "foo", ['f', 'o', 'o'], orderMatters=False)        

        #will FAIL - second 'o' not in expectedResults
        assertIteration( "foo", ['f', 'o'], orderMatters=False)

        # will FAIL - 'x' not present in iterable
        assertIteration( "foo", ['f', 'o', 'o', 'x'], orderMatters=False))

        # will PASS - order irrelevant
        assertIteration( "foo", ['o', 'f', 'o'], orderMatters=False)
        #################################################
        """
        
        expectedResults = list(expectedResults)
        if onlyMembershipMatters:
            unmatchedResults = set(expectedResults)
        else:
            unmatchedResults = list(expectedResults)
        for item in iterable:
            notInExpectedResultsFormat = \
                "iterable '%s' contained item '%s', not found in %s '%s'"
                
            if onlyMembershipMatters:
                self.assertTrue(item in expectedResults,
                                notInExpectedResultsFormat % (iterable, item, "expectedResults", expectedResults))
            else:
                self.assertTrue(item in unmatchedResults,
                                notInExpectedResultsFormat % (iterable, item, "unmatched expectedResults", unmatchedResults))

                # should do above test even if orderMatters, since that way we will get a Fail (as opposed to an Error)
                # if len(unmatchedResults)==0
                if orderMatters:
                    self.assertEqual(item, unmatchedResults[0], "iterable returned '%s' when '%s' was expected" % (item, unmatchedResults[0]))
            if item in unmatchedResults:
                unmatchedResults.remove(item)
            
        message = "iterable '%s' did not contain expected item(s): %s" % (iterable, [str(x) for x in unmatchedResults])
        self.assertEqual(len(unmatchedResults), 0, message)


# TODO: move to util.math?
def permutations(sequence, length=None):
    """Given a sequence, will return an iterator over the possible permutations.
    
    If length is 'None', the permutations will default to having the same length
    as the sequence; otherwise, the returned permtuations will have the given length.
    
    Note that every element in the sequence is considered unique, so that there may be
    'duplicate' permutations if there are duplicate elements in seq, ie:
    
    perumutations("aa") -> ['a', 'a'] and ['a', 'a']
    """
    
    if length is None:
        length = len(sequence)
    elif length < 0 or length > len(sequence):
        raise ValueError("Permutation length '%i' invalid for %s" % (length, sequence))
        
    if length==0: yield []
    
    else:
        for i in xrange(len(sequence)):
            for subpermutation in permutations(sequence[:i] + sequence[i+1:], length - 1):
                yield [sequence[i]] + subpermutation


def isOneToOne(dict):
    """
    Tests if the given dictionary is one to one (if dict[x]==dict[y], x==y)
    """
    return len(set(dict.itervalues())) == len(dict)
                
def isEquivalenceRelation(inputs, outputs, dict):
    """
    Tests if the given dictionary defines an equivalence relation from between inputs and outputs.
    
    Technically, tests if the dict is bijective: ie, one-to-one (if dict[x]==dict[y], x==y) and
    onto (for every y in outputs, exists an x such that dict[x] == y)
    """
    inputs = set(inputs)
    output = set(outputs)
    if len(inputs) == len(outputs) and \
        set(dict.iterkeys()) == inputs and \
        set(dict.itervalues()) == outputs:
        
        return True
    else:
        return False
    
class SuiteFromTestModule(TestSuite):
    def __init__(self, moduleName, suiteFuncName=SUITE_FUNC_NAME):
        super(SuiteFromTestModule, self).__init__()
        self.moduleName = moduleName
        self.suiteFuncName = suiteFuncName
        self._importTestModule()
        self._importSuite()
        self._makeTestCase()
        self.addTest(self.testCase)
        if self.importedSuite:
            self.addTest(self.importedSuite)
        
    def _importTestModule(self):
        self._importError = None
        try:
            self.module = __import__(self.moduleName)
            
            # if moduleName is 'package.module', __import__ returns package!
            packagePath = self.moduleName.split('.')
            for subModule in packagePath[1:]:
                self.module = getattr(self.module, subModule)
        except:
            self._importError = lastFormattedException()
            self.module = None
            
    def _importSuite(self):
        self.importedSuite = None
        if self.module:
            try:
                self.suiteFunc = getattr(self.module, self.suiteFuncName)
                self.importedSuite = suiteFunc()
            except:
                pass

            if not self.importedSuite:
                self.importedSuite = default_suite(self.module)

        if (not isinstance(self.importedSuite, TestSuite)
            or not self.importedSuite.countTestCases()):
            self.importedSuite = None

    def _makeTestCase(self):
        class TestSuiteImport(TestCaseExtended):
            def runTest(self_testcase):
                self_testcase.assertTrue(self.module, "Failed to import module '%s':\n%s" % (self.moduleName, self._importError))
                #self_testcase.assertTrue(self.importedSuite, "Failed to create a test suite from module '%s'" % self.moduleName)
            runTest.__doc__ = """Try to import module '%s'""" % self.moduleName
        self.testCase = TestSuiteImport()

# TODO: find ALL doctest-able modules as well!
def suite():
    suite = TestSuite()
    for testMod in findTestModules():
        suite.addTest(SuiteFromTestModule(testMod))
    return suite
    

def findPymelTestModules(module, testModulePrefix="test_"):
    """
    Will return the name of test modules used for unit testing the given module.
    
    If testModuleExactName is True, then module should be the name of the module
    that contains the unittesting code, ie 'test_utilitypes'; otherwise, it should
    be the name of a module (ie, 'utilitytypes') or the module object itself that
    we wish to find a unittest package for.
    
    The return results will include the given module.
    """
    foundMods = []
    if isinstance(module, types.ModuleType):
        moduleName = module.__name__
    else:
        moduleName = module

    foundMods.append(moduleName)
        
    # NOTE: For now, I'm ignoring the possibility of modules with the same name,
    # but within different pacakges - ie, 'package.aModule' and 'nextPackage.aModule'    
    
    # If we were fed a package name, ie 'pymel.util.utilitytypes', get just
    # the final name, ie 'utilitytypes'
    shortName = moduleName.split('.')[-1]

    if testModulePrefix:
        shortName = testModulePrefix + shortName
    
    for testModule in findTestModules():
        if testModule.split('.')[-1] == shortName:
            foundMods.append(testModule)
    return foundMods


def pymel_test(module=None, testModuleExactName=False, testModulePrefix="test_"):
    """
    Run pymel unittests / doctests
    
    To run tests for a module, use pymel_test(module),
    where module can be the full module path string:
    >>> pymel_test('pymel.core.pmtypes.pmcmds')  #doctest: +ELLIPSIS
    ...
    
    ...or it can be an actual module object:
    >>> import pymel.tools.mel2py as mel2py
    >>> pymel_test(mel2py) #doctest: +ELLIPSIS
    ...

    If pymel_test is given no arguments, it runs all known tests:
    >>> pymel_test() #doctest: +ELLIPSIS
    ...
    """

    if not module:
        theSuite = suite()
    else:
        testModuleNames = findPymelTestModules(module, testModulePrefix=testModulePrefix)
        theSuite = TestSuite()
        for mod in testModuleNames:
            theSuite.addTest(SuiteFromTestModule(mod))
        
    if theSuite.countTestCases():
        MayaTestRunner().run(theSuite)
    else:
        print("Could not find any tests for '%s'" % module)

#================================================================================
# Following code modified from python 2.5.1 source code, in module:
#   lib\test\regrtest.py
#================================================================================
STDTESTS = []
NOTTESTS = []
def findTestModules(testdir=None, stdtests=STDTESTS, nottests=NOTTESTS, package="__thisPackage__", testModulePrefix="test_"):
    """Return a list of all applicable test modules."""
    if package == "__thisPackage__":
        package = ".".join(__name__.split(".")[:-1])
    if testdir is None:
        testdir = findtestdir()
    names = os.listdir(testdir)
    tests = []
    for name in names:
        if name[:len(testModulePrefix)] == testModulePrefix and name[-3:] == os.extsep+"py":
            modname = name[:-3]
            if package:
                modname = package + "." + modname
            if modname not in stdtests and modname not in nottests:
                tests.append(modname)
    tests.sort()
    return stdtests + tests

def findtestdir():
    if __name__ == '__main__':
        file = sys.argv[0]
    else:
        file = __file__
    testdir = os.path.dirname(file) or os.curdir
    return testdir

#===============================================================================
#  End of code originally from python 2.5.1
#===============================================================================