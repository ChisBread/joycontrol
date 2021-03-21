import argparse
import asyncio
import logging
import os
import socket
import re

# from yamakai

import hid

from joycontrol import logging_default as log, utils
from joycontrol.device import HidDevice
from joycontrol.server import PROFILE_PATH
from joycontrol.utils import AsyncHID

logger = logging.getLogger(__name__)

async def myPipe(src, dest):
    while data := await src():
        await dest(data)

def read_from_sock(sock):
    async def internal():
        return await asyncio.get_event_loop().sock_recv(sock, 500)
    return internal

def write_to_sock(sock):
    async def internal(data):
        return await asyncio.get_event_loop().sock_sendall(sock, data)
    return internal

async def connect_bt(bt_addr):
    loop = asyncio.get_event_loop()
    ctl = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET, socket.BTPROTO_L2CAP)
    itr = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET, socket.BTPROTO_L2CAP)

    # See https://bugs.python.org/issue27929?@ok_message=issue%2027929%20versions%20edited%20ok&@template=item
    # bug here: https://github.com/python/cpython/blob/5e29021a5eb10baa9147fd977cab82fa3f652bf0/Lib/asyncio/selector_events.py#L495
    # should be
    # if hasattr(socket, 'AF_INET') or hasattr(socket, 'AF_INET6') sock.family in (socket.AF_INET, socket.AF_INET6):
    # or something similar
    # ctl.setblocking(0)
    # itr.setblocking(0)
    # await loop.sock_connect(ctl, (bt_addr, 17))
    # await loop.sock_connect(itr, (bt_addr, 19))
    ctl.connect((bt_addr, 17))
    itr.connect((bt_addr, 19))
    ctl.setblocking(0)
    itr.setblocking(0)
    return ctl, itr

def bt_to_callbacks(ctl, itr):
    def internal():
        itr.close()
        ctl.close()
    return read_from_sock(itr), write_to_sock(itr), internal

async def connectEth(eth, server=False):
    loop = asyncio.get_event_loop()
    ip, port = eth.split(':')
    port = int(port)
    s = socket.socket()
    s.setblocking(0)
    if server:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', port))
        s.listen(1)
        while 1:
            c, caddr = await loop.sock_accept(s)
            if caddr[0] == ip:
                s.close()
                c.setblocking(0)
                s = c
                break
            else:
                print("unexpecetd host", caddr)
                c.close()
    else:
        await loop.sock_connect(s, (ip, port))
    # make the data f****** go
    s.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
    return s

def eth_to_callbacks(sock):
    return read_from_sock(sock), write_to_sock(sock), lambda: sock.close()

async def _main(sw_addr, jc_addr):
    # loop = asyncio.get_event_loop()

    jc_eth = not re.match("([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}", jc_addr)
    sw_eth = not re.match("([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}", sw_addr)

    print("jc_eth", jc_eth, "sw_eth", sw_eth)

    send_to_jc = None
    recv_from_jc = None
    cleanup_jc = None

    send_to_switch = None
    recv_from_switch = None
    cleanup_switch = None
    try:
        # DONT do if-else here, because order should be easily adjustable
        if not jc_eth:
            print("waiting for joycon")
            recv_from_jc, send_to_jc, cleanup_jc = bt_to_callbacks(*await connect_bt(jc_addr))

        if jc_eth:
            print("opening joycon eth")
            recv_from_jc, send_to_jc, cleanup_jc = eth_to_callbacks(await connectEth(jc_addr, True))
            #print("waiting for initial packet")
            #print(await recv_from_jc())
            #print("got initial")

        if sw_eth:
            print("opening switch eth")
            recv_from_switch, send_to_switch, cleanup_switch = eth_to_callbacks(await connectEth(sw_addr, False))
            #print("waiting for initial packet")
            #print (await recv_from_switch())
            #print("got initial")

        if not sw_eth:
            print("waiting for switch")
            recv_from_switch, send_to_switch, cleanup_switch = bt_to_callbacks(*await connect_bt(sw_addr))


        print("stared forwarding")
        await asyncio.gather(
            asyncio.ensure_future(myPipe(recv_from_switch, send_to_jc)),
            asyncio.ensure_future(myPipe(recv_from_jc, send_to_switch)),
        )
    finally:
        if cleanup_switch:
            cleanup_switch()
        if cleanup_jc:
            cleanup_jc()



if __name__ == '__main__':
    # check if root
    if not os.geteuid() == 0:
        raise PermissionError('Script must be run as root!')

    parser = argparse.ArgumentParser(description="Acts as proxy for Switch-joycon communtcation between the two given addresses.\n Start the instance forwarding to the Switch directly first")
    parser.add_argument('-S', '--switch', type=str, default=None,
                        help='talk to switch at the given address. Either a BT-MAC or a tcp ip:port combo.')
    parser.add_argument('-J', '--joycon', type=str, default=None,
                        help='talk to switch at the given address. Either a BT-MAC or a tcp ip:port combo.')

    args = parser.parse_args()
    if not args.switch or not args.joycon:
        print("missing args")
        exit(1)

    asyncio.run(_main(args.switch, args.joycon))
