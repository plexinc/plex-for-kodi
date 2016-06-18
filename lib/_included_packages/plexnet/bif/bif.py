import os
import struct


class Bif(object):
    def __init__(self, path):
        self.path = path
        self.size = 0
        self.frames = []
        self.maxTimestamp = 0
        self.timestampMultiplier = 1000
        self.readHeader()

    def readHeader(self):
        dataFormat = '<8s4sII44x'
        with open(self.path, 'rb') as f:
            (
                self.magic,
                version,
                self.size,
                self.timestampMultiplier

            ) = struct.unpack(dataFormat, f.read(struct.calcsize(dataFormat)))
            import binascii
            print binascii.hexlify(self.magic)
            return
            self.frames = []
            last = None
            for x in range(self.size + 1):
                fdata = {}
                (
                    fdata['timestamp'],
                    fdata['offset']
                ) = struct.unpack('<II', f.read(8))

                fdata['timestamp'] *= (self.timestampMultiplier / 1000.0)

                if last:
                    last['size'] = fdata['offset'] - last['offset']

                last = fdata
                self.frames.append(fdata)

            del self.frames[-1]  # Remove last frame as it just shows the end of the last actual frame

            self.maxTimestamp = self.frames[-1]['timestamp']

    def getImageData(self, idx):
        fdata = self.data['frames'][idx]
        with open(self.path, 'rb') as f:
            f.seek(fdata['offset'])
            return f.read(fdata['size'])

    def dumpImages(self, target_dir_path):
        with open(self.path, 'rb') as s:
            for i in range(self.size):
                with open(os.path.join(target_dir_path, str(i) + '.jpg'), 'wb') as f:
                    fdata = self.frames[i]
                    s.seek(fdata['offset'])
                    f.write(s.read(fdata['size']))
