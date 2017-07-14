"""
Copyright (C) 2017 Stanislav Bobovych
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.
You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

import argparse
import os
import struct
import shutil

CM_ID_CONST = {'CMSF':0x00, 'CMA':0x02, 'CMBN':0x04, 'CMFI':0x06, 'CMRT':0x08, 'CMBS':0x0A, 'CMFB':0x0C}
CM_CONST_ID = {0x00:'CMSF', 0x02:'CMA', 0x04:'CMBN', 0x06:'CMFI', 0x08:'CMRT', 0x0A:'CMBS', 0x0C:'CMFB'}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Tool for experimenting with Combat Mission btt files.')
    parser.add_argument('-t', '--type', required=True, choices=['CMSF', 'CMA', 'CMBN', 'CMFI', 'CMRT', 'CMBS', 'CMFB'], help='Output map type')
    parser.add_argument('-o', '--outdir', default=os.getcwd(), help='Output path')
    parser.add_argument('file', nargs='?', help='Input file')

    args = parser.parse_args()
    indir = os.path.split(args.file)[0]
    infile = os.path.split(args.file)[1]    
    basename,extension = os.path.splitext(infile)
    new_basename = basename + "_" + args.type
    outfile = new_basename + extension
    outdir = args.outdir

    with open(args.file, 'rb') as f:
        f.seek(0x10)
        map_type, = struct.unpack("H", f.read(2))
        print("Input map type:", CM_CONST_ID[map_type])

    outfile_full_path = os.path.join(outdir, outfile)
    shutil.copy(args.file, outfile_full_path)

    with open(outfile_full_path, 'r+b') as f:
        f.seek(0x10)
        type_bytes = struct.pack("H", CM_ID_CONST[args.type])
        f.write(type_bytes)
        print("Generated output map:", outfile)

    #TODO game version follows game id
