from cpu.bytes import Byte, Byte32

class Chunk(Byte32):
    """Central Base class for a Chunk Type"""
    def __init__(self):
        super().__init__()
        self.ssdpath = "/ssd/chunks/static.ssd"

class ChunkInputOuput(Chunk):
    """ Manages Chunk Input Output on files"""
    def __init__(self):
        super().__init__()

class SSD(ChunkInputOuput):
    """SSD API for the Usage"""
    def __init__(self):
        super().__init__()