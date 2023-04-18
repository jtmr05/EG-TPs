import typing


def annotate(src: typing.Any, *ansi_escape_codes: int) -> str:

    length: int = len(ansi_escape_codes)
    if length == 0:
        return str(src)

    import io
    str_buffer: io.StringIO = io.StringIO()

    str_buffer.write(f"\033[{ansi_escape_codes[0]}")
    for i in range(1, length):
        str_buffer.write(f";{ansi_escape_codes[i]}")
    str_buffer.write(f"m{str(src)}\033[0m")

    return str_buffer.getvalue()
