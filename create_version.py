import argparse
from typing import cast


def set_template(maj: str, min: str, patch: str, name: str) -> str:
    return f"""
# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
ffi=FixedFileInfo(
# filevers and prodvers should be always a tuple with four items: (1, 2, 3, 4)
# Set not needed items to zero 0.
filevers=({maj}, {min}, {patch}, 0),
prodvers=({maj}, {min}, {patch}, 0),
# Contains a bitmask that specifies the valid bits 'flags'r
mask=0x3f,
# Contains a bitmask that specifies the Boolean attributes of the file.
flags=0x0,
# The operating system for which this file was designed.
# 0x4 - NT and there is no need to change it.
OS=0x4,
# The general type of file.
# 0x1 - the file is an application.
fileType=0x1,
# The function of the file.
# 0x0 - the function is not defined for this fileType
subtype=0x0,
# Creation date and time stamp.
date=(0, 0)
),
kids=[
StringFileInfo(
[
StringTable(
    u'040904B0',
    [StringStruct(u'CompanyName', u'Enycs'),
    StringStruct(u'FileDescription', u'{name}'),
    StringStruct(u'FileVersion', u'{maj}.{min}.{patch}'),
    StringStruct(u'InternalName', u'{name}'),
    StringStruct(u'LegalCopyright', u'Copyright (c) Enycs'),
    StringStruct(u'OriginalFilename', u'{name}.exe'),
    StringStruct(u'ProductName', u'{name}'),
    StringStruct(u'ProductVersion', u'{maj}.{min}.{patch}')])
]),
VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
]
)
"""


def main() -> None:
    # Create the parser
    parser = argparse.ArgumentParser(description="Convert requirements from .xlsx to .vti-tso.")

    parser.add_argument("-o", "--output", type=str, help="The output version file.")
    parser.add_argument("-v", "--version", type=str, help="The actual version.")
    parser.add_argument("-n", "--name", type=str, help="Name of the actual app.")
    parser.add_argument(
        "-nv", "--nameAndVersion", type=str, help='Name and version of the actual app separated by "_".'
    )

    # Parse the arguments
    args = parser.parse_args()
    if args.nameAndVersion:
        splitted = args.nameAndVersion.strip().split("=")[-1].strip().split("_")
        name = splitted[0].replace('"', "")
        version = splitted[1].replace('"', "")
    else:
        version = cast(str, args.version).strip().replace('"', "").split("=")[-1].strip()
        name = args.name

    maj, min, patch = tuple(version.split("."))

    with open(args.output, "wt") as out_file:
        out_file.write(set_template(maj, min, patch, name))


if __name__ == "__main__":
    main()
