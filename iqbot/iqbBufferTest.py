from buffer import genericBuffer, quoteBuffer, historyBuffer, bufferManager, bufferFactory
import unittest

class TestQuoteBuffer(unittest.TestCase):
    def setUp(self):
        self.testline = "quote line 1"
        self.testline2 = "quote line 2"

    def testQuoteBufferAddLineGetLine(self):
        quote = quoteBuffer()
        quote.addLine(self.testline)
        quote.addLine(self.testline2)
        self.assertEquals(quote.getLine(1), self.testline)
        self.assertEquals(quote.getLine(2), self.testline2)

class TestHistoryBuffer(unittest.TestCase):
    def setUp(self):
        self.testline = "history line 1"
        self.testline2 = "history line 2"
        self.testline3 = "history line 3"

    def testHistoryBufferAddLineGetLine(self):
        history = historyBuffer(2)
        history.addLine(self.testline)
        history.addLine(self.testline2)
        self.assertEquals(history.getLine(1), self.testline)
        self.assertEquals(history.getLine(2), self.testline2)

    def testHistoryBufferMaxSize(self):
        history = historyBuffer(2)
        history.addLine(self.testline)
        history.addLine(self.testline2)
        history.addLine(self.testline3)
        self.assertEquals(history.getLine(1), self.testline2)

    def testGetMaxSize(self):
        history = historyBuffer(10)
        self.assertEquals(history.getMaxSize(), 10)

    def testMaxSizeNotExceeded(self):
        history = historyBuffer(2)
        history.addLine(self.testline)
        history.addLine(self.testline2)
        history.addLine(self.testline3)
        self.assertEquals(history.getSize(), history.getMaxSize())

class TestGenericBuffer(unittest.TestCase):
    def setUp(self):
        self.testline = "generic line 1"
        self.testline2 = "generic line 2"
        self.testline3 = "generic line 3"

    def testRemoveLineFront(self):
        generic = genericBuffer()
        generic.addLine(self.testline)
        generic.addLine(self.testline2)
        generic.addLine(self.testline3)
        generic.deleteLine(1)
        self.assertEquals(generic.getLine(1), self.testline2)

    def testRemoveLineMiddle(self):
        generic = genericBuffer()
        generic.addLine(self.testline)
        generic.addLine(self.testline2)
        generic.addLine(self.testline3)
        generic.deleteLine(2)
        self.assertEquals(generic.getLine(2), self.testline3)

    def testRemoveLineEnd(self):
        generic = genericBuffer()
        generic.addLine(self.testline)
        generic.addLine(self.testline2)
        generic.addLine(self.testline3)
        generic.deleteLine(3)
        self.assertEquals(generic.getLine(2), self.testline2)

    def testGetSize(self):
        generic = genericBuffer()
        self.assertEquals(generic.getSize(), 0)
        generic.addLine(self.testline)
        self.assertEquals(generic.getSize(), 1)

    def testGetLineException(self):
        generic = genericBuffer()
        self.assertRaises(IndexError, generic.getLine, 1)

    def testGetNegativeLine(self):
        generic = genericBuffer()
        generic.addLine(self.testline)
        generic.addLine(self.testline2)
        generic.addLine(self.testline3)
        self.assertEquals(generic.getLine(-1), self.testline3)

    def testGetZerothLine(self):
        generic = genericBuffer()
        generic.addLine(self.testline)
        self.assertRaises(IndexError, generic.getLine, 0)

class TestBufferManager(unittest.TestCase):
    def setUp(self):
        self.testline = "generic line 1"
        self.testline2 = "generic line 2"
        self.testline3 = "generic line 3"
        self.testline4 = "generic line 4"
        self.testline5 = "generic line 5"
        self.testline6 = "generic line 6"
        self.manager = bufferManager(bufferFactory(), 2)

        self.rangeManager = bufferManager(bufferFactory(), 3)
        self.rangeManager.getHistoryBuffer().addLine(self.testline)
        self.rangeManager.getHistoryBuffer().addLine(self.testline2)
        self.rangeManager.getHistoryBuffer().addLine(self.testline3)
        self.rangeManager.addQuoteBuffer('test')
        self.rangeManager.getQuoteBuffer('test').addLine(self.testline4)
        self.rangeManager.getQuoteBuffer('test').addLine(self.testline5)
        self.rangeManager.getQuoteBuffer('test').addLine(self.testline6)

    def testGetHistoryBuffer(self):
        self.manager.history.addLine(self.testline)
        self.assertEquals(self.manager.history.getLine(1), self.manager.getHistoryBuffer().getLine(1))

    def testAddQuoteBuffer(self):
        self.manager.addQuoteBuffer('test')
        self.manager.getQuoteBuffer('test').addLine(self.testline)
        self.assertEquals(self.manager.quotes['test'].getLine(1), self.testline)

    def testGetQuoteBuffer(self):
        self.manager.addQuoteBuffer('test')
        self.manager.quotes['test'].addLine(self.testline)
        self.assertEquals(self.manager.quotes['test'].getLine(1), self.manager.getQuoteBuffer('test').getLine(1))

    def testDeleteQuoteBuffer(self):
        manager = bufferManager(bufferFactory(), 2)
        manager.addQuoteBuffer('test')
        manager.deleteQuoteBuffer('test')
        self.assertRaises(KeyError, manager.getQuoteBuffer, 'test')

    def testGetHistoryLine(self):
        self.manager.getHistoryBuffer().addLine(self.testline)
        self.assertEquals(self.manager.getHistoryLine(1), self.testline)

    def testGetQuoteLine(self):
        manager = bufferManager(bufferFactory(), 2)
        manager.addQuoteBuffer('test')
        manager.getQuoteBuffer('test').addLine(self.testline)
        self.assertEquals(manager.getQuoteLine(1, 'test'), self.testline)

    def testGetLineHistoryLine(self):
        manager = bufferManager(bufferFactory(), 2)
        manager.getHistoryBuffer().addLine(self.testline)
        self.assertEquals(manager.getLine('#1', 'test'), self.testline)

    def testGetLineQuoteLine(self):
        manager = bufferManager(bufferFactory(), 2)
        manager.addQuoteBuffer('test')
        manager.getQuoteBuffer('test').addLine(self.testline)
        self.assertEquals(manager.getLine('1', 'test'), self.testline)
    
    def testGetLineNegativeHistoryLine(self):
        manager = bufferManager(bufferFactory(), 2)
        manager.getHistoryBuffer().addLine(self.testline)
        self.assertEquals(manager.getLine('#-1', 'test'), self.testline)

    def testGetLineNegativeQuoteLine(self):
        manager = bufferManager(bufferFactory(), 2)
        manager.addQuoteBuffer('test')
        manager.getQuoteBuffer('test').addLine(self.testline)
        self.assertEquals(manager.getLine('-1', 'test'), self.testline)

    def testMultipleQuoteBuffers(self):
        manager = bufferManager(bufferFactory(), 2)
        manager.addQuoteBuffer('test1')
        manager.addQuoteBuffer('test2')
        manager.getQuoteBuffer('test1').addLine(self.testline)
        manager.getQuoteBuffer('test2').addLine(self.testline2)
        self.assertNotEquals(manager.getQuoteLine(1, 'test1'), manager.getQuoteLine(1, 'test2'))
        self.assertEquals(manager.getQuoteLine(1, 'test1'), self.testline)
        self.assertEquals(manager.getQuoteLine(1, 'test2'), self.testline2)

    def testAddDuplicateQuoteBuffer(self):
        manager = bufferManager(bufferFactory(), 2)
        manager.addQuoteBuffer('test1')
        self.assertRaises(KeyError, manager.addQuoteBuffer, 'test1')

    # P = Positive, N = negative, A = ascending, D = descending
    def testGetLineRangeHistoryPPA(self):
        self.assertEquals(self.rangeManager.getRange('#2,#3', None), [self.testline2, self.testline3])

    def testGetLineRangeHistoryPPD(self):
        self.assertEquals(self.rangeManager.getRange('#3,#2', None), [self.testline2, self.testline3])

    def testGetLineRangeHistoryNNA(self):
        self.assertEquals(self.rangeManager.getRange('#-3,#-2', None), [self.testline, self.testline2])

    def testGetLineRangeHistoryNND(self):
        self.assertEquals(self.rangeManager.getRange('#-2,#-3', None), [self.testline, self.testline2])

    def testGetLineRangeHistoryPNA(self):
        self.assertEquals(self.rangeManager.getRange('#2,#-1', None), [self.testline2, self.testline3])

    def testGetLineRangeHistoryPND(self):
        self.assertEquals(self.rangeManager.getRange('#3,#-2', None), [self.testline2, self.testline3])

    def testGetLineRangeHistoryNPD(self):
        self.assertEquals(self.rangeManager.getRange('#-1,#2', None), [self.testline2, self.testline3])

    def testGetLineRangeHistoryNPA(self):
        self.assertEquals(self.rangeManager.getRange('#-2,#3', None), [self.testline2, self.testline3])

    def testGetLineRangeQuotePPA(self):
        self.assertEquals(self.rangeManager.getRange('2,3', 'test'), [self.testline5, self.testline6])

    def testGetLineRangeQuotePPD(self):
        self.assertEquals(self.rangeManager.getRange('3,2', 'test'), [self.testline5, self.testline6])

    def testGetLineRangeQuoteNNA(self):
        self.assertEquals(self.rangeManager.getRange('-3,-2', 'test'), [self.testline4, self.testline5])

    def testGetLineRangeQuoteNND(self):
        self.assertEquals(self.rangeManager.getRange('-2,-3', 'test'), [self.testline4, self.testline5])

    def testGetLineRangeQuotePNA(self):
        self.assertEquals(self.rangeManager.getRange('2,-1', 'test'), [self.testline5, self.testline6])

    def testGetLineRangeQuotePND(self):
        self.assertEquals(self.rangeManager.getRange('3,-2', 'test'), [self.testline5, self.testline6])

    def testGetLineRangeQuoteNPD(self):
        self.assertEquals(self.rangeManager.getRange('-1,2', 'test'), [self.testline5, self.testline6])

    def testGetLineRangeQuoteNPA(self):
        self.assertEquals(self.rangeManager.getRange('-2,3', 'test'), [self.testline5, self.testline6])

class TestBufferFactory(unittest.TestCase):
    def testCreateQuoteBuffer(self):
        factory = bufferFactory()
        self.assert_(isinstance(factory.createQuoteBuffer(), quoteBuffer))

    def testCreateHistoryBuffer(self):
        factory = bufferFactory()
        self.assert_(isinstance(factory.createHistoryBuffer(2), historyBuffer))

if __name__ == "__main__":
    unittest.main()
