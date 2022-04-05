#!/usr/bin/env python3

import ftplib
import io, re, sys
from random import randint

debug = False

def establishFTP(ip, port, user, password, folder, use_passive):

    try:
        ftp = ftplib.FTP()
        ftp.connect(ip, port)
        ftp.login(user, password)
        ftp.set_pasv(use_passive)
        ftp.cwd(folder)
    except ftplib.all_errors as e:
        print(f"Failed to connect to FTP server (Response: {e})", file=sys.stderr)
        sys.exit(1)

    return ftp

def ls(ftp):

    files = []
    ftp.dir(files.append)
    if debug:
        for fi in files:
            print(fi)
        print()
    return files

def createCovertFile(ftp, data: int, order: int):
    filename = f'file{order:05}'
    if debug:
        print(f'creating {filename} with {data & 0x1FF:03o} permissions')
    if data & 0x200:
        data &= 0x1FF
        ftp.mkd(filename)
    else:
        ftp.storbinary(f'STOR {filename}', io.BytesIO(b'dummy text'))
    ftp.sendcmd(f'SITE CHMOD {data:o} {filename}')

def createDummyFile(ftp, order: int):
    data = randint(0x80, 0x3FF)
    createCovertFile(ftp, data, order)

def permStringToBinary(perms: str) -> int:
    binaryString = ''
    for ch in perms:
        if ch in ['d', 'l', 'r', 'w', 'x']:
            binaryString += '1'
        elif ch == '-':
            binaryString += '0'

    return binaryString

def covertWrite(ftp, message: str, base10: bool = False):

    if base10:
        binaryStr = ''.join(format(ord(i), '07b') for i in message)
        binaryStr += '0' * (10 - len(binaryStr) % 10)

        for i in range(0, len(binaryStr), 10):
            createCovertFile(ftp, int(binaryStr[i:i+10],2), i//10)

    else:
        i = 0
        while len(message) > 0:
            if randint(0,10) > 3:
                createCovertFile(ftp, ord(message[0]), i)
                message = message[1:]
            else:
                createDummyFile(ftp, i)
            i += 1


def covertRead(ftp, base10: bool = False) -> str:

    permRegex = re.compile('^[dlrwx-]{10}')
    fileList = ls(ftp)
    binaryString = ''
    message = ''

    for f in fileList:
        permString = permRegex.search(f)[0]
        c = permStringToBinary(permString)

        if base10:
            binaryString += c
        elif int(c, 2) < 0x80:
            message += chr(int(c, 2))

    if base10:
        for i in range(0, len(binaryString), 7):
            message += chr(int(binaryString[i:i+7], 2))

    return message

def main():
    import getopt

    ip = "138.47.99.64"
    port = 21
    user = "anonymous"
    password = ""
    folder = "/"
    use_passive = True
    base10 = False
    encode = False
    message = ''

    usageString = f"""Reads or writes a covert message to/from an FTP server

Usage: {sys.argv[0]} [-w|--write <message>] [-H|--host <host>] [-P|--port <port>] \
[-d|--dir <directory>] [-u|--user <username>] [-p|--pass <password>] [-v|--verbose]"""

    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], \
                "H:P:d:p:hu:vbw:", ["host=", "pass=", "dir=", "port=", "help", "user=", "verbose", "base10", "write="])
    except getopt.GetoptError as e:
        print(e, file=sys.stderr)
        print(usageString, file=sys.stderr)
        sys.exit(2)

    for opt, arg in opts:
        if opt in ["-h", "--help"]:
            print(usageString)
            sys.exit()
        elif opt in ["-H", "--host"]:
            ip = arg
        elif opt in ["-P", "--port"]:
            port = int(arg)
        elif opt in ["-d", "--dir"]:
            folder = arg
        elif opt in ["-u", "--user"]:
            user = arg
        elif opt in ["-p", "--pass"]:
            password = arg
        elif opt in ["-v", "--verbose"]:
            global debug
            debug = True
        elif opt in ["-b", "--base10"]:
            base10 = True
        elif opt in ["-e", "--encode"]:
            encode = True
            message = arg

    f = establishFTP(ip, port, user, password, folder, use_passive)

    try:
        if encode:
            covertWrite(f, message, base10)
            print("Message printed successfully")
        else:
            print(covertRead(f, base10))
    except ftplib.all_errors as e:
        print(f"Operation failed (Response: {e})", file=sys.stderr)
        sys.exit(1)
    finally:
        f.quit()

if __name__ == '__main__':
    main()
