"""Tk precise-scroll deltas: signed X/Y packed into a 32-bit integer (TIP 684)."""


def touchpad_deltas(raw):
    raw=int(raw)&0xffffffff
    x=(raw>>16)&0xffff;y=raw&0xffff
    return (x-0x10000 if x&0x8000 else x,y-0x10000 if y&0x8000 else y)
