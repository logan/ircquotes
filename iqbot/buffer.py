class genericBuffer:
    def __init__(self):
        self.lines = []

    def __repr__(self):
        return self.lines.__str__()

    def addLine(self, line):
        self.lines.append(line)

    def getLine(self, lineNumber):
        if lineNumber > 0:
            return self.lines[lineNumber - 1]
        elif lineNumber < 0:
            return self.lines[lineNumber]
        else:
            raise IndexError

    def getRange(self, start, end):
        if start < 0:
            start = len(self.lines) + start + 1
        if end < 0:
            end = len(self.lines) + end + 1

        if start > end:
            (start, end) = (end, start)

        return self.lines[start - 1:end]

    def deleteLine(self, lineNumber):
        self.lines = self.lines[0:lineNumber - 1] + self.lines[lineNumber:]

    def getSize(self):
        return len(self.lines)

class quoteBuffer(genericBuffer):
    pass

class historyBuffer(genericBuffer):
    def __init__(self, maxSize):
        self.maxSize = maxSize
        genericBuffer.__init__(self)

    def addLine(self, line):
        if self.getSize() == self.getMaxSize():
            self.deleteLine(1)
        genericBuffer.addLine(self, line)

    def getMaxSize(self):
        return self.maxSize

class bufferManager:
    def __init__(self, bufferFactory, historyBufferSize = None):
        self.bufferFactory = bufferFactory
        self.history = bufferFactory.createHistoryBuffer(historyBufferSize)
        self.quotes = {}

    def getHistoryBuffer(self):
        return self.history

    def addQuoteBuffer(self, quoteId):
        if self.quotes.has_key(quoteId):
            raise KeyError
        self.quotes[quoteId] = self.bufferFactory.createQuoteBuffer()

    def getQuoteBuffer(self, quoteId):
        return self.quotes[quoteId]

    def deleteQuoteBuffer(self, quoteId):
        del(self.quotes[quoteId])

    def getHistoryLine(self, lineNumber):
        return self.history.getLine(lineNumber)

    def getQuoteLine(self, lineNumber, quoteId):
        return self.quotes[quoteId].getLine(lineNumber)

    def getLine(self, lineString, quoteId):
        if lineString[0] == '#':
            return self.history.getLine(int(lineString[1:]))
        else:
            return self.quotes[quoteId].getLine(int(lineString))

    def getRange(self, lineString, quoteId):
        (start, end) = lineString.split(',')
        if start[0] == '#' and end[0] == '#':
            return self.history.getRange(int(start[1:]), int(end[1:]))
        else:
            return self.quotes[quoteId].getRange(int(start), int(end))

class bufferFactory:
    def createQuoteBuffer(self):
        return quoteBuffer()

    def createHistoryBuffer(self, maxSize = None):
        return historyBuffer(maxSize)
