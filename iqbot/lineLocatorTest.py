from lineLocator import lineLocator, ircLine, ircBuffer, ircHistoryBuffer
import unittest

class TestLineLocator(unittest.TestCase):
    def setUp(self):
        self.locator = lineLocator()
        self.historyLines = [ircLine('history #1', 1), ircLine('history #2', 2)]
        self.quoteLines = [ircLine('quote #1', 3), ircLine('quote #2', 4)]

    def testGetLineHistory(self):
        line = self.locator.getLines('#1')
        self.assertEquals(self.historyLines[0:1], line)

    def testGetLineHistoryOneLineRange(self):
        line = self.locator.getLines('#1,#1')
        self.assertEquals(self.historyLines[0:1], line)

    def testGetLineHistoryTwoLineRange(self):
        line = self.locator.getLines('#1,#2')
        self.assertEquals(self.historyLines[0:2], line)

    def testGetLineQuote(self):
        line = self.locator.getLines('1')
        self.assertEquals(self.quoteLines[0:1], line)

    def testGetLineQuoteOneLineRange(self):
        line = self.locator.getLines('1,1')
        self.assertEquals(self.quoteLines[0:1], line)

    def testGetLineQuoteTwoLineRange(self):
        line = self.locator.getLines('1,2')
        self.assertEquals(self.quoteLines[0:2], line)

    def testGetHistoryLines(self):
        line = self.locator.getHistoryLines(1)
        self.assertEquals(self.historyLines[0:1], line)

    def testGetHistoryLinesOneLineRange(self):
        line = self.locator.getHistoryLines(1,1)
        self.assertEquals(self.historyLines[0:1], line)

    def testGetHistoryLinesTwoLineRange(self):
        line = self.locator.getHistoryLines(1,2)
        self.assertEquals(self.historyLines[0:2], line)

    def testGetQuoteLines(self):
        line = self.locator.getQuoteLines(1)
        self.assertEquals(self.quoteLines[0:1], line)

    def testGetQuoteLinesOneLineRange(self):
        line = self.locator.getQuoteLines(1,1)
        self.assertEquals(self.quoteLines[0:1], line)

    def testGetQuoteLinesTwoLineRange(self):
        line = self.locator.getQuoteLines(1,2)
        self.assertEquals(self.quoteLines[0:2], line)

class TestIrcBuffer(unittest.TestCase):
    def testAdd(self):
        buf = ircBuffer()
        buf.addLine(ircLine('history #1', 1))
        self.assertEquals(buf.lines, [ircLine('history #1', 1)])

    def testRemove(self):
        buf = ircBuffer()
        buf.addLine(ircLine('history #1', 1))
        buf.addLine(ircLine('history #2', 2))
        buf.addLine(ircLine('history #3', 3))
        buf.removeLine(ircLine('history #2', 2))
        self.assertEquals(buf.lines, [ircLine('history #1', 1), ircLine('history #3', 3)])

class TestIrcHistoryBuffer(unittest.TestCase):
    def testAddEmpty(self):
        buf = ircHistoryBuffer(10)
        size = buf.size
        start = buf.startLine
        end = buf.endLine
        buf.addLine('history #1')
        self.assertEquals(buf.size, size + 1)
        self.assertEquals(buf.startLine, start)
        self.assertEquals(buf.endLine, end + 1)

    def testGetOneLine(self):
        buf = ircHistoryBuffer(2)
        buf.addLine('history #1')
        self.assertEquals([ircLine('history #1', 1)], buf.getLines(1,1))

    def testGetRolledLine(self):
        buf = ircHistoryBuffer(2)
        buf.addLine('history #1')
        buf.addLine('history #2')
        buf.addLine('history #3')
        buf.addLine('history #4')
        self.assertEquals([ircLine('history #3', 3), ircLine('history #4', 4)], buf.getLines(1,2))

    def testGetHistoryLine(self):
        buf = ircHistoryBuffer(2)
        buf.addLine('history #1')
        buf.addLine('history #2')
        buf.addLine('history #3')
        buf.addLine('history #4')
        self.assertEquals([ircLine('history #3', 3), ircLine('history #4', 4)], buf.getHistoryLines(3,4))

    def testGetHistoryLine(self):
        buf = ircHistoryBuffer(10)
        for i in range(1,11):
            buf.addLine('history #%d' % (i,))
        self.assertEquals([ircLine('history #3', 3), ircLine('history #4', 4)], buf.getHistoryLines(3,4))

if __name__ == "__main__":
    unittest.main()
