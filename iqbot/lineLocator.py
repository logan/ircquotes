class ircLine:
    def __init__(self, lineText, historyLine):
        self.lineText = lineText
        self.historyLine = historyLine

    def __cmp__(self, line):
        return cmp([self.historyLine, self.lineText], 
                   [line.historyLine, line.lineText])

class ircBuffer:
    def __init__(self):
        self.lines = []

    def addLine(self, line):
        self.lines.append(line)

    def removeLine(self, line):
        self.lines.remove(line)

class ircHistoryBuffer(ircBuffer):
    def __init__(self, maxsize):
        ircBuffer.__init__(self)
        self.startLine = 0
        self.endLine = 0
        self.maxsize = maxsize
        self.size = 0

    def addLine(self, line):
        if self.size < self.maxsize:
            self.size += 1
        else:
            self.lines = self.lines[1:]
            self.startLine += 1
        self.endLine += 1
        ircBuffer.addLine(self, ircLine(line, self.endLine))

    def getHistoryLines(self, start, end):
        if start > end:
            (start, end) = (end, start)
        if self.startLine > 0:
            start -= (self.endLine - 2)
            end -= (self.endLine - 2)
        return self.getLines(start, end)

    def getLines(self, start, end):
        return self.lines[start - 1:end]


class ircQuoteBuffer(ircBuffer):
    pass

class lineLocator:
    history = [ircLine('history #1', 1), 
               ircLine('history #2', 2),
               ircLine('quote #1', 3),
               ircLine('quote #2', 4)]
    quote = [ircLine('quote #1', 3), ircLine('quote #2', 4)]

    def getLines(self, lines):
        if lines.find(',') >= 0:
            (begin, end) = lines.split(',')
        else:
            (begin, end) = (lines, None)

        useHistory = False
        if begin[0] == '#':
            useHistory = True
            begin = begin[1:]
        begin = int(begin)

        if end is not None:
            if end[0] == '#':
                useHistory = True
                end = end[1:]
            end = int(end)

        if useHistory:
            return self.getHistoryLines(begin, end)
        else:
            return self.getQuoteLines(begin, end)

    def getBufferLines(self, buffer, begin, end = None):
        if end is not None:
            if begin > end:
                (begin, end) = (end, begin)
            return buffer[begin - 1:end]
        else:
            return buffer[0:begin]

    def getHistoryLines(self, begin, end = None):
        return self.getBufferLines(self.history, begin, end)

    def getQuoteLines(self, begin, end = None):
        return self.getBufferLines(self.quote, begin, end)
