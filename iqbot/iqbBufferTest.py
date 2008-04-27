from buffer import genericBuffer, quoteBuffer, historyBuffer, bufferManager, bufferFactory, historyLine
import unittest

class TestQuoteBuffer(unittest.TestCase):
    def setUp(self):
        self.testline = historyLine("quote line 1", 0)
        self.testline2 = historyLine("quote line 2", 1)

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
        self.histline = historyLine(self.testline, 0)
        self.histline2 = historyLine(self.testline2, 1)
        self.histline3 = historyLine(self.testline3, 2)

    def testHistoryBufferAddLineGetLine(self):
        history = historyBuffer(2)
        history.addLine(self.testline)
        history.addLine(self.testline2)
        self.assertEquals(history.getLine(1), self.histline)
        self.assertEquals(history.getLine(2), self.histline2)

    def testHistoryBufferMaxSize(self):
        history = historyBuffer(2)
        history.addLine(self.testline)
        history.addLine(self.testline2)
        history.addLine(self.testline3)
        self.assertEquals(history.getLine(1), self.histline2)

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
        self.testline = historyLine("generic line 1", 0)
        self.testline2 = historyLine("generic line 2", 1)
        self.testline3 = historyLine("generic line 3", 2)

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
        self.histline = historyLine(self.testline, 0)
        self.histline2 = historyLine(self.testline2, 1)
        self.histline3 = historyLine(self.testline3, 2)
        self.histline4 = historyLine(self.testline, 0)
        self.histline5 = historyLine(self.testline2, 1)
        self.histline6 = historyLine(self.testline3, 2)

        self.manager = bufferManager(bufferFactory(), 2)

        self.rangeManager = bufferManager(bufferFactory(), 3)
        self.rangeManager.getHistoryBuffer().addLine(self.testline)
        self.rangeManager.getHistoryBuffer().addLine(self.testline2)
        self.rangeManager.getHistoryBuffer().addLine(self.testline3)
        self.rangeManager.addQuoteBuffer('test')
        self.rangeManager.getQuoteBuffer('test').addLine(self.histline4)
        self.rangeManager.getQuoteBuffer('test').addLine(self.histline5)
        self.rangeManager.getQuoteBuffer('test').addLine(self.histline6)

    def testGetHistoryBuffer(self):
        self.manager.history.addLine(self.testline)
        self.assertEquals(self.manager.history.getLine(1), self.manager.getHistoryBuffer().getLine(1))

    def testAddQuoteBuffer(self):
        self.manager.addQuoteBuffer('test')
        self.manager.getQuoteBuffer('test').addLine(self.histline)
        self.assertEquals(self.manager.quotes['test'].getLine(1), self.histline)

    def testGetQuoteBuffer(self):
        self.manager.addQuoteBuffer('test')
        self.manager.quotes['test'].addLine(self.histline)
        self.assertEquals(self.manager.quotes['test'].getLine(1), self.manager.getQuoteBuffer('test').getLine(1))

    def testDeleteQuoteBuffer(self):
        manager = bufferManager(bufferFactory(), 2)
        manager.addQuoteBuffer('test')
        manager.deleteQuoteBuffer('test')
        self.assertRaises(KeyError, manager.getQuoteBuffer, 'test')

    def testGetHistoryLine(self):
        self.manager.getHistoryBuffer().addLine(self.testline)
        self.assertEquals(self.manager.getHistoryLine(1), self.histline)

    def testGetQuoteLine(self):
        manager = bufferManager(bufferFactory(), 2)
        manager.addQuoteBuffer('test')
        manager.getQuoteBuffer('test').addLine(self.histline)
        self.assertEquals(manager.getQuoteLine(1, 'test'), self.histline)

    def testGetLineHistoryLine(self):
        manager = bufferManager(bufferFactory(), 2)
        manager.getHistoryBuffer().addLine(self.testline)
        self.assertEquals(manager.getLine('#1', 'test'), self.histline)

    def testGetLineQuoteLine(self):
        manager = bufferManager(bufferFactory(), 2)
        manager.addQuoteBuffer('test')
        manager.getQuoteBuffer('test').addLine(self.histline)
        self.assertEquals(manager.getLine('1', 'test'), self.histline)
    
    def testGetLineNegativeHistoryLine(self):
        manager = bufferManager(bufferFactory(), 2)
        manager.getHistoryBuffer().addLine(self.testline)
        self.assertEquals(manager.getLine('#-1', 'test'), self.histline)

    def testGetLineNegativeQuoteLine(self):
        manager = bufferManager(bufferFactory(), 2)
        manager.addQuoteBuffer('test')
        manager.getQuoteBuffer('test').addLine(self.histline)
        self.assertEquals(manager.getLine('-1', 'test'), self.histline)

    def testMultipleQuoteBuffers(self):
        manager = bufferManager(bufferFactory(), 2)
        manager.addQuoteBuffer('test1')
        manager.addQuoteBuffer('test2')
        manager.getQuoteBuffer('test1').addLine(self.histline)
        manager.getQuoteBuffer('test2').addLine(self.histline2)
        self.assertNotEquals(manager.getQuoteLine(1, 'test1'), manager.getQuoteLine(1, 'test2'))
        self.assertEquals(manager.getQuoteLine(1, 'test1'), self.histline)
        self.assertEquals(manager.getQuoteLine(1, 'test2'), self.histline2)

    def testAddDuplicateQuoteBuffer(self):
        manager = bufferManager(bufferFactory(), 2)
        manager.addQuoteBuffer('test1')
        self.assertRaises(KeyError, manager.addQuoteBuffer, 'test1')

    # P = Positive, N = negative, A = ascending, D = descending
    def testGetRangeHistoryPPA(self):
        self.assertEquals(self.rangeManager.getRange('#2,#3', None), [self.histline2, self.histline3])

    def testGetRangeHistoryPPD(self):
        self.assertEquals(self.rangeManager.getRange('#3,#2', None), [self.histline2, self.histline3])

    def testGetRangeHistoryNNA(self):
        self.assertEquals(self.rangeManager.getRange('#-3,#-2', None), [self.histline, self.histline2])

    def testGetRangeHistoryNND(self):
        self.assertEquals(self.rangeManager.getRange('#-2,#-3', None), [self.histline, self.histline2])

    def testGetRangeHistoryPNA(self):
        self.assertEquals(self.rangeManager.getRange('#2,#-1', None), [self.histline2, self.histline3])

    def testGetRangeHistoryPND(self):
        self.assertEquals(self.rangeManager.getRange('#3,#-2', None), [self.histline2, self.histline3])

    def testGetRangeHistoryNPD(self):
        self.assertEquals(self.rangeManager.getRange('#-1,#2', None), [self.histline2, self.histline3])

    def testGetRangeHistoryNPA(self):
        self.assertEquals(self.rangeManager.getRange('#-2,#3', None), [self.histline2, self.histline3])

    def testGetRangeQuotePPA(self):
        self.assertEquals(self.rangeManager.getRange('2,3', 'test'), [self.histline5, self.histline6])

    def testGetRangeQuotePPD(self):
        self.assertEquals(self.rangeManager.getRange('3,2', 'test'), [self.histline5, self.histline6])

    def testGetRangeQuoteNNA(self):
        self.assertEquals(self.rangeManager.getRange('-3,-2', 'test'), [self.histline4, self.histline5])

    def testGetRangeQuoteNND(self):
        self.assertEquals(self.rangeManager.getRange('-2,-3', 'test'), [self.histline4, self.histline5])

    def testGetRangeQuotePNA(self):
        self.assertEquals(self.rangeManager.getRange('2,-1', 'test'), [self.histline5, self.histline6])

    def testGetRangeQuotePND(self):
        self.assertEquals(self.rangeManager.getRange('3,-2', 'test'), [self.histline5, self.histline6])

    def testGetRangeQuoteNPD(self):
        self.assertEquals(self.rangeManager.getRange('-1,2', 'test'), [self.histline5, self.histline6])

    def testGetRangeQuoteNPA(self):
        self.assertEquals(self.rangeManager.getRange('-2,3', 'test'), [self.histline5, self.histline6])

    def testGetRangeMixedPPA(self):
        self.assertEquals(self.rangeManager.getRange('#2,3', 'test'), [self.histline2, self.histline3])

    def testGetRangeMixedPPD(self):
        self.assertEquals(self.rangeManager.getRange('3,#2', 'test'), [self.histline2, self.histline3])

    def testGetRangeMixedNPA(self):
        self.assertEquals(self.rangeManager.getRange('#-2,3', 'test'), [self.histline2, self.histline3])

    def testGetRangeMixedPND(self):
        self.assertEquals(self.rangeManager.getRange('3,#-2', 'test'), [self.histline2, self.histline3])

    def testGetRangeMixedPNA(self):
        self.assertEquals(self.rangeManager.getRange('#2,-1', 'test'), [self.histline2, self.histline3])
        
    def testAbsoluteRangeOverflow(self):
        manager = bufferManager(bufferFactory(), 3)
        manager.getHistoryBuffer().addLine(self.testline)
        manager.getHistoryBuffer().addLine(self.testline)
        manager.getHistoryBuffer().addLine(self.testline2)
        manager.getHistoryBuffer().addLine(self.testline3)
        manager.addQuoteBuffer('test')
        manager.getQuoteBuffer('test').addLine(manager.getHistoryLine(2))
        manager.getQuoteBuffer('test').addLine(manager.getHistoryLine(3))

        self.assertEquals(manager.getRange('#1,1', 'test'), [manager.getHistoryLine(1), manager.getHistoryLine(2)])

class TestBufferFactory(unittest.TestCase):
    def testCreateQuoteBuffer(self):
        factory = bufferFactory()
        self.assert_(isinstance(factory.createQuoteBuffer(), quoteBuffer))

    def testCreateHistoryBuffer(self):
        factory = bufferFactory()
        self.assert_(isinstance(factory.createHistoryBuffer(2), historyBuffer))

class TestHistoryLine(unittest.TestCase):
    def testEquality(self):
        line1 = historyLine('test words', 1)
        line2 = historyLine('test words', 2)
        line3 = historyLine('words test', 3)
        line4 = historyLine('test words', 1)
        self.assertNotEquals(line1, line2)
        self.assertNotEquals(line1, line3)
        self.assertEquals(line1, line4)
if __name__ == "__main__":
    unittest.main()
